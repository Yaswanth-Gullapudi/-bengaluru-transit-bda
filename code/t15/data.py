"""Download raw data, load it in pandas, and ingest it into HDFS with Spark."""
from __future__ import annotations

import json
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from . import config as C

ACCESS_API = "https://api.github.com/repos/urbanmorph/RAS-PT/contents/src/public/stops_accessibility"
ACCESS_RAW = "https://raw.githubusercontent.com/urbanmorph/RAS-PT/main/src/public/stops_accessibility/{name}"


# ----------------------------------------------------------------- download
def _get(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": "t15-research-client"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    return dest


def raw_dir() -> Path:
    return C.paths()["raw"]


def download_all(snapshots: list[str] | None = None, accessibility: bool = True):
    """Fetch every open dataset into data_raw/. Skips files already present.

    On Kaggle, run this once, then save data_raw/ as a private Dataset so the
    other notebooks (and the second account) can attach it without downloading.
    """
    p = C.paths()
    raw = p["raw"] if (p["raw"] / "metro").exists() else p["raw_writable"]
    for key, rel in C.METRO_FILES.items():
        _get(f"{C.METRO_REPO_RAW}/{rel}", raw / "metro" / Path(rel).name)
    for name in ("station-names.csv", "station-codes.csv"):
        _get(f"{C.METRO_REPO_RAW}/raw/{name}", raw / "metro" / name)
    _get(C.METRO_GTFS_URL, raw / "metro_gtfs" / "bmrcl.zip")
    for date in snapshots or list(C.BMTC_SNAPSHOTS):
        sha = C.BMTC_SNAPSHOTS[date]
        dest = raw / "gtfs" / f"bmtc_{date}.zip"
        if not dest.exists():
            print("GTFS", date)
        _get(C.BMTC_GTFS_URL.format(sha=sha), dest)
    if accessibility:
        req = urllib.request.Request(ACCESS_API, headers={"User-Agent": "t15-research-client"})
        listing = json.load(urllib.request.urlopen(req, timeout=60))
        for item in listing:
            _get(ACCESS_RAW.format(name=item["name"]), raw / "accessibility" / item["name"])
    print("Raw data ready in", raw)
    return raw


# ----------------------------------------------------------------- metro (pandas)
def _metro_path(key: str) -> Path:
    return raw_dir() / "metro" / Path(C.METRO_FILES[key]).name


def load_station_hourly(kind: str = "entries") -> pd.DataFrame:
    """Station x date x hour counts. kind = 'entries' or 'exits'."""
    d = pd.read_parquet(_metro_path(kind))
    d = d.rename(columns={"Date": "date", "Hour": "hour", "Station": "station", "Ridership": kind})
    d["date"] = d["date"].astype(str)
    d["station"] = d["station"].astype(str)
    return d


def load_od() -> pd.DataFrame:
    d = pd.read_parquet(_metro_path("od"))
    d = d.rename(columns={"Date": "date", "Hour": "hour", "Origin Station": "origin",
                          "Destination Station": "dest", "Ridership": "trips",
                          "Travelled Stations": "hops", "Fare Slab": "fare_slab",
                          "Fare": "fare", "Revenue": "revenue"})
    for c in ("date", "origin", "dest"):
        d[c] = d[c].astype(str)
    return d


def metro_stations() -> pd.DataFrame:
    """83 stations with coordinates, entrances and line(s) from the BMRCL GTFS."""
    z = zipfile.ZipFile(raw_dir() / "metro_gtfs" / "bmrcl.zip")
    stops = pd.read_csv(z.open("stops.txt"), dtype={"parent_station": str, "stop_id": str})
    names = set(load_station_hourly("entries")["station"].unique())
    parents = stops[(stops["location_type"] == 1) & stops["stop_name"].isin(names)].copy()
    entr = stops[(stops["location_type"] == 2) & stops["parent_station"].isin(parents["stop_id"])]
    trips = pd.read_csv(z.open("trips.txt"), dtype=str)
    st = pd.read_csv(z.open("stop_times.txt"), dtype={"stop_id": str, "trip_id": str},
                     usecols=["trip_id", "stop_id"])
    plat = stops[stops["parent_station"].notna()][["stop_id", "parent_station"]]
    st = st.merge(plat, on="stop_id", how="left")
    st["parent"] = st["parent_station"].fillna(st["stop_id"])
    lines = (st.merge(trips[["trip_id", "route_id"]], on="trip_id")
             .groupby("parent")["route_id"].agg(lambda s: "+".join(sorted(set(s)))))
    parents["lines"] = parents["stop_id"].map(lines).fillna("")
    out = parents.rename(columns={"stop_name": "station", "stop_id": "code",
                                  "stop_lat": "lat", "stop_lon": "lon"})[
        ["station", "code", "lat", "lon", "lines"]]
    out["is_yellow_new"] = out["station"].isin(C.YELLOW_NEW)
    out["is_interchange_rv"] = out["station"] == C.INTERCHANGE
    out["is_old"] = ~out["is_yellow_new"]
    ent = entr.rename(columns={"stop_lat": "lat", "stop_lon": "lon"})[["parent_station", "lat", "lon"]]
    ent = ent.merge(out[["code", "station"]], left_on="parent_station", right_on="code")[["station", "lat", "lon"]]
    # stations without mapped entrances fall back to the station point
    missing = out[~out["station"].isin(ent["station"])][["station", "lat", "lon"]]
    out.attrs["entrances"] = pd.concat([ent, missing], ignore_index=True)
    return out.reset_index(drop=True)


def yellow_alignment() -> pd.DataFrame:
    """Ordered coordinates of Yellow Line stations (RV Road first)."""
    s = metro_stations()
    order = [C.INTERCHANGE] + C.YELLOW_NEW
    return s.set_index("station").loc[order, ["lat", "lon"]].reset_index()


# ----------------------------------------------------------------- BMTC GTFS (pandas)
def gtfs_path(date: str) -> Path:
    return raw_dir() / "gtfs" / f"bmtc_{date}.zip"


def load_gtfs(date: str, tables=("stops", "routes", "trips", "stop_times", "calendar")) -> dict:
    z = zipfile.ZipFile(gtfs_path(date))
    out = {}
    for t in tables:
        name = f"{t}.txt"
        if name not in z.namelist():
            continue
        kw = {"dtype": str}
        if t == "stop_times":
            kw["usecols"] = ["trip_id", "stop_id", "stop_sequence"]
        out[t] = pd.read_csv(z.open(name), **kw)
    if "stops" in out:
        for col in ("stop_lat", "stop_lon"):
            out["stops"][col] = out["stops"][col].astype(float)
    if "stop_times" in out:
        out["stop_times"]["stop_sequence"] = out["stop_times"]["stop_sequence"].astype(int)
    return out


def weekday_trips(g: dict) -> pd.DataFrame:
    """Trips that run on a typical Wednesday (all trips if no calendar)."""
    trips = g["trips"]
    cal = g.get("calendar")
    if cal is not None and "wednesday" in cal:
        ok = set(cal.loc[cal["wednesday"].astype(int) == 1, "service_id"])
        if ok:
            trips = trips[trips["service_id"].isin(ok)]
    return trips


# ----------------------------------------------------------------- accessibility (booths)
def load_booths() -> pd.DataFrame:
    """Polling-booth polygons with 2022 population and 2018 bus-access metrics (RAS-PT)."""
    rows = []
    for f in sorted((raw_dir() / "accessibility").glob("*.geojson")):
        g = json.load(open(f, encoding="utf-8"))
        for feat in g["features"]:
            p = feat["properties"]
            ring = feat["geometry"]["coordinates"][0] if feat["geometry"] else []
            if feat["geometry"] and feat["geometry"]["type"] == "MultiPolygon":
                ring = feat["geometry"]["coordinates"][0][0]
            if not ring:
                continue
            lon = sum(pt[0] for pt in ring) / len(ring)
            lat = sum(pt[1] for pt in ring) / len(ring)
            rows.append({"booth": p.get("BoothCode"), "ac_code": p.get("AC_CODE"),
                         "ac_name": p.get("AC_Name"), "people": p.get("people") or 0,
                         "employees": p.get("employees") or 0,
                         "access_pct_2018": p.get("access_percentage"),
                         "trips_2018": p.get("trips"), "lat": lat, "lon": lon})
    b = pd.DataFrame(rows)
    b["people"] = b["people"].clip(lower=0)          # a few booths have negative counts
    b = b[b["lat"].between(12.6, 13.4) & b["lon"].between(77.2, 77.9)]   # drop stray geometry
    return b.reset_index(drop=True)


# ----------------------------------------------------------------- OpenCity ward files
def load_ward_files() -> dict:
    """Read whatever was downloaded from OpenCity 'Bus stops and routes map by ward'
    into data_raw/ward/. Accepts .kml, .kmz, .geojson, .csv, .xlsx. Returns {filename: GeoDataFrame/DataFrame}.
    """
    import geopandas as gpd
    out = {}
    d = raw_dir() / "ward"
    if not d.exists() and C.paths()["env"] == "kaggle":       # also accept a separate dataset
        hits = sorted({Path(c).parent for c in C.kaggle_glob("ac1*-stops.csv")})
        d = hits[0] if hits else d
    if not d.exists():
        print("No data_raw/ward folder: download the OpenCity files and add them to the Kaggle Dataset.")
        return out
    for f in sorted(d.iterdir()):
        suf = f.suffix.lower()
        try:
            if suf in (".kml", ".kmz"):
                import fiona
                fiona.drvsupport.supported_drivers["KML"] = "rw"
                fiona.drvsupport.supported_drivers["LIBKML"] = "rw"
                src = f"/vsizip/{f}" if suf == ".kmz" else str(f)
                layers = fiona.listlayers(src)
                out[f.name] = pd.concat([gpd.read_file(src, layer=l).assign(layer=l) for l in layers],
                                        ignore_index=True)
            elif suf in (".geojson", ".json", ".shp", ".gpkg"):
                out[f.name] = gpd.read_file(f)
            elif suf == ".csv":
                out[f.name] = pd.read_csv(f)
            elif suf in (".xlsx", ".xls"):
                out[f.name] = pd.read_excel(f)
        except Exception as exc:
            print("Could not read", f.name, "->", exc)
    for k, v in out.items():
        print(f"{k}: {len(v)} rows, columns = {list(v.columns)[:12]}")
    return out


# ----------------------------------------------------------------- Spark ingest
def ingest_to_hdfs(spark, snapshots: list[str] | None = None, overwrite: bool = False):
    """Write metro tables and all GTFS snapshots to HDFS as parquet.

    GTFS tables are partitioned by `snapshot` so later jobs can prune by date.
    """
    from pyspark.sql import functions as F
    from .env import hdfs_path

    raw = raw_dir()
    mode = "overwrite" if overwrite else "ignore"
    for key in C.METRO_FILES:
        pdf = {"entries": lambda: load_station_hourly("entries"),
               "exits": lambda: load_station_hourly("exits"),
               "od": load_od}[key]()
        spark.createDataFrame(pdf).write.mode(mode).parquet(hdfs_path(f"metro/{key}"))
    stations = metro_stations()
    spark.createDataFrame(stations).write.mode(mode).parquet(hdfs_path("metro/stations"))

    tmp = Path("/tmp/t15_gtfs_unzipped") if C.paths()["env"] != "local" else C.paths()["cache"] / "gtfs_unzipped"
    for date in (list(C.BMTC_SNAPSHOTS) if snapshots is None else snapshots):
        zp = raw / "gtfs" / f"bmtc_{date}.zip"
        if not zp.exists():
            print("missing", zp.name)
            continue
        d = tmp / date
        if not d.exists():
            zipfile.ZipFile(zp).extractall(d, members=[m for m in zipfile.ZipFile(zp).namelist()
                                                       if m in ("stops.txt", "routes.txt", "trips.txt",
                                                                "stop_times.txt", "calendar.txt")])
        for t in ("stops", "routes", "trips", "stop_times", "calendar"):
            f = d / f"{t}.txt"
            part = f"gtfs/{t}/snapshot={date}"     # Hive-style partition folder
            if not f.exists() or (hdfs_has(spark, part) and not overwrite):
                continue
            df = spark.read.option("header", True).csv(f"file://{f}")
            df.write.mode("overwrite").parquet(hdfs_path(part))
        print("ingested GTFS", date)


def hdfs_has(spark, name: str) -> bool:
    from .env import hdfs_path
    jvm = spark._jvm
    path = jvm.org.apache.hadoop.fs.Path(hdfs_path(name))
    fs = path.getFileSystem(spark._jsc.hadoopConfiguration())
    return fs.exists(path)
