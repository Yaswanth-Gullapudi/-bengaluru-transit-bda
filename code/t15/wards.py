"""Population and ward-level analysis.

Inputs
* RAS-PT booth data (urbanmorph/RAS-PT, shown on bmtc.vonter.top/bus_stops_accessibility):
  polling-booth polygons with 2022 electoral-roll population and 2018 bus-stop access.
* OpenCity "Bus stops and routes map by ward" files placed in data_raw/ward/
  (download manually in a browser; the site blocks scripts).

Outputs
* population within 400/800 m of each metro station (an ML feature and a control)
* per ward (or per assembly constituency if no ward file): who gained direct metro
  access from the Yellow Line, and who has a bus link to it
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import bus as B
from . import config as C
from . import data as D


def station_population(booths: pd.DataFrame | None = None, radius_m: float = 800) -> pd.Series:
    booths = booths if booths is not None else D.load_booths()
    st = D.metro_stations()
    pop = {}
    for _, s in st.iterrows():
        d = B.haversine(s["lat"], s["lon"], booths["lat"].values, booths["lon"].values)
        pop[s["station"]] = booths.loc[d <= radius_m, "people"].sum()
    return pd.Series(pop, name=f"pop_{int(radius_m)}m")


def booth_access(booths: pd.DataFrame | None = None, snapshot: str = C.SNAPSHOT_BEFORE,
                 walk_bus_m: float = 400, walk_metro_m: float = 800) -> pd.DataFrame:
    """For each booth: distance to nearest old / new metro station, and whether a bus stop
    within `walk_bus_m` has a weekday trip reaching the Yellow corridor (straight-line)."""
    booths = (booths if booths is not None else D.load_booths()).copy()
    st = D.metro_stations()
    lat, lon = booths["lat"].values, booths["lon"].values
    def nearest(mask):
        d = np.full(len(booths), np.inf)
        for _, s in st[mask].iterrows():
            d = np.minimum(d, B.haversine(s["lat"], s["lon"], lat, lon))
        return d
    booths["d_old_metro"] = nearest(~st["is_yellow_new"].values)
    booths["d_new_yellow"] = nearest(st["is_yellow_new"].values)
    booths["metro_before"] = booths["d_old_metro"] <= walk_metro_m
    booths["metro_after"] = booths["metro_before"] | (booths["d_new_yellow"] <= walk_metro_m)
    booths["gained_direct_metro"] = booths["metro_after"] & ~booths["metro_before"]

    g = D.load_gtfs(snapshot)
    stops = g["stops"]
    trips = D.weekday_trips(g)[["trip_id"]]
    stt = g["stop_times"].merge(trips, on="trip_id")
    corridor = set()
    for _, s in st[st["is_yellow_new"]].iterrows():
        d = B.haversine(s["lat"], s["lon"], stops["stop_lat"].values, stops["stop_lon"].values)
        corridor |= set(stops.loc[d <= C.CORRIDOR_M, "stop_id"])
    link_trips = set(stt.loc[stt["stop_id"].isin(corridor), "trip_id"])
    linked_stops = set(stt.loc[stt["trip_id"].isin(link_trips), "stop_id"])
    lstops = stops[stops["stop_id"].isin(linked_stops)]
    # nearest linked stop for every booth (vectorised in chunks)
    best = np.full(len(booths), np.inf)
    la, lo = lstops["stop_lat"].values, lstops["stop_lon"].values
    for i in range(0, len(booths), 500):
        sl = slice(i, i + 500)
        d = B.haversine(lat[sl, None], lon[sl, None], la[None, :], lo[None, :])
        best[sl] = d.min(axis=1)
    booths["d_bus_to_yellow"] = best
    booths["bus_link_yellow"] = best <= walk_bus_m
    return booths


def _ward_polygons():
    """Find a polygon layer with ward names among the OpenCity files, if present."""
    files = D.load_ward_files()
    for name, df in files.items():
        if hasattr(df, "geometry") and df.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).mean() > 0.5:
            namecol = next((c for c in df.columns if c.lower() in ("name", "ward_name", "wardname", "ward")),
                           None)
            if namecol is None:
                namecol = next((c for c in df.columns if df[c].dtype == object and c != "geometry"), None)
            print(f"Using ward polygons from {name} (name column: {namecol}, {len(df)} wards)")
            return df[[namecol, "geometry"]].rename(columns={namecol: "ward"}).to_crs(4326)
    return None


def area_summary(booths_acc: pd.DataFrame) -> pd.DataFrame:
    """Aggregate booth access to wards (OpenCity polygons) or, failing that, to
    assembly constituencies. Shares are population-weighted."""
    import geopandas as gpd
    wards = _ward_polygons()
    b = booths_acc.copy()
    if wards is not None:
        pts = gpd.GeoDataFrame(b, geometry=gpd.points_from_xy(b["lon"], b["lat"]), crs=4326)
        b = gpd.sjoin(pts, wards, how="left", predicate="within").drop(columns=["geometry", "index_right"])
        key = "ward"
    else:
        print("No ward polygons found; summarising by assembly constituency instead.")
        key = "ac_name"
    w = b["people"]
    agg = b.assign(
        pop_metro_before=w * b["metro_before"], pop_metro_after=w * b["metro_after"],
        pop_gained=w * b["gained_direct_metro"], pop_bus_link=w * b["bus_link_yellow"],
        pop_bus_link_only=w * (b["bus_link_yellow"] & ~b["metro_after"]),
        access2018_w=w * b["access_pct_2018"].fillna(0) / 100,
    ).groupby(key)[["people", "pop_metro_before", "pop_metro_after", "pop_gained", "pop_bus_link",
                    "pop_bus_link_only", "access2018_w"]].sum()
    for c in ["pop_metro_before", "pop_metro_after", "pop_gained", "pop_bus_link", "pop_bus_link_only"]:
        agg[c.replace("pop_", "share_")] = agg[c] / agg["people"]
    agg["bus_access_2018"] = agg["access2018_w"] / agg["people"]
    return agg.drop(columns="access2018_w").sort_values("share_gained", ascending=False).reset_index()


def load_opencity_stop_csvs() -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Read the OpenCity 'Stops with Number of Trips' CSVs (one per assembly constituency, 2018 data)
    and the 'BMTC Stops with Location and Routes' CSV. Columns are detected by name."""
    import re
    files = D.load_ward_files()
    per_ac, routes = [], None
    for name, df in files.items():
        if not name.lower().endswith(".csv"):
            continue
        cols = {c.lower().strip(): c for c in df.columns}
        lat = next((cols[c] for c in cols if "lat" in c), None)
        lon = next((cols[c] for c in cols if "lon" in c or "lng" in c), None)
        if lat is None or lon is None:
            print(f"skip {name}: no lat/lon columns ({list(df.columns)})")
            continue
        m = re.search(r"ac\s*-?\s*(\d{3})", name, flags=re.I)
        if m is None:                       # citywide "Stops with Location and Routes" file
            routes = df.rename(columns={lat: "lat", lon: "lon"})
            continue
        trips = next((cols[c] for c in cols if "trip" in c), None)
        stop = next((cols[c] for c in cols if "name" in c or "stop" in c), None)
        booth = next((cols[c] for c in cols if "booth" in c), None)
        ac_code = (df[booth].astype(str).str[2:5] if booth else m.group(1))
        out = pd.DataFrame({"ac_code": ac_code, "ac_file": name,
                            "stop_name": df[stop] if stop else None,
                            "lat": pd.to_numeric(df[lat], errors="coerce"),
                            "lon": pd.to_numeric(df[lon], errors="coerce"),
                            "trips_2018": pd.to_numeric(df[trips], errors="coerce") if trips else np.nan})
        # the same stop is listed once per nearby polling booth: keep one row per stop
        out = out.dropna(subset=["lat", "lon"]).drop_duplicates(subset=["lat", "lon"])
        per_ac.append(out.dropna(subset=["lat", "lon"]))
    stops = pd.concat(per_ac, ignore_index=True) if per_ac else pd.DataFrame()
    print(f"OpenCity: {len(stops)} stop rows from {len(per_ac)} constituency files;",
          "routes file found" if routes is not None else "no routes file")
    return stops, routes


def ac_service_change(snapshot: str = C.SNAPSHOT_BEFORE, match_m: float = 100) -> pd.DataFrame | None:
    """Per assembly constituency: 2018 stops and trips (OpenCity / myBMTC) vs the 2025 GTFS.
    Each 2018 stop is matched to the nearest 2025 GTFS stop within `match_m` metres."""
    stops18, _ = load_opencity_stop_csvs()
    if stops18.empty:
        print("Add the OpenCity CSVs (dataset t15-ward) to run this.")
        return None
    g = D.load_gtfs(snapshot, tables=("stops", "trips", "stop_times", "calendar"))
    trips = D.weekday_trips(g)[["trip_id"]]
    per_stop = g["stop_times"].merge(trips, on="trip_id").groupby("stop_id")["trip_id"].nunique()
    s25 = g["stops"].assign(trips_2025=lambda d: d["stop_id"].map(per_stop).fillna(0))
    la, lo = s25["stop_lat"].values, s25["stop_lon"].values
    idx, dist = np.empty(len(stops18), int), np.empty(len(stops18))
    for i in range(0, len(stops18), 500):
        sl = slice(i, i + 500)
        d = B.haversine(stops18["lat"].values[sl, None], stops18["lon"].values[sl, None], la[None, :], lo[None, :])
        idx[sl], dist[sl] = d.argmin(axis=1), d.min(axis=1)
    stops18["matched"] = dist <= match_m
    stops18["trips_2025"] = np.where(stops18["matched"], s25["trips_2025"].values[idx], np.nan)
    names = D.load_booths().assign(ac_code=lambda d: d["ac_code"].astype(str)).groupby("ac_code")["ac_name"].first()
    stops18["ac_file"] = stops18["ac_code"].map(names).fillna("AC " + stops18["ac_code"].astype(str))
    agg = stops18.groupby(["ac_code", "ac_file"]).agg(
        stops_2018=("lat", "size"), trips_2018=("trips_2018", "sum"),
        matched_share=("matched", "mean"), trips_2025_matched=("trips_2025", "sum")).reset_index()
    matched_2018 = stops18[stops18["matched"]].groupby("ac_code")["trips_2018"].sum()
    agg["trips_2018_matched"] = agg["ac_code"].map(matched_2018)
    agg["trip_change_pct"] = (agg["trips_2025_matched"] / agg["trips_2018_matched"] - 1) * 100
    return agg.sort_values("trip_change_pct")
