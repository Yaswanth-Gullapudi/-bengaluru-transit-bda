"""Bus-network measures built from BMTC GTFS.

* walking distance from each metro station (via its entrances) to nearby bus stops
* the bus-link score per metro station (BusTrips, YellowLink, Collinear, ...)
* bus supply around metro stations across all GTFS snapshots (pandas and Spark)
"""
from __future__ import annotations

import hashlib
import json
import pickle
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config as C
from . import data as D

EARTH_R = 6_371_000.0
DETOUR_FALLBACK = 1.3      # walk / straight-line ratio used only if OSM is unavailable


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_R * np.arcsin(np.sqrt(a))


# ----------------------------------------------------------------- walking network
class WalkRouter:
    """Walking distances from each metro station's entrances to bus stops.

    Downloads ONE OpenStreetMap walking network covering all metro stations (+1.5 km),
    caches it as GraphML, and runs a multi-source Dijkstra from each station's
    entrances with a distance cutoff. Falls back to straight line x 1.3 if OSM fails.
    """

    def __init__(self, stations: pd.DataFrame, cutoff_m: float = C.CORRIDOR_M, use_osm: bool = True):
        self.stations = stations
        self.cutoff = cutoff_m
        self.use_osm = use_osm
        self.cache = C.paths()["cache"] / "walk"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.G = None
        self._trees: dict = {}
        self.osm_ok: dict = {}
        ent = stations.attrs.get("entrances")
        self.entrances = ent if ent is not None else D.metro_stations().attrs["entrances"]

    def _graph(self):
        if self.G is not None or not self.use_osm:
            return self.G
        import osmnx as ox
        gfile = self.cache / "bengaluru_metro_walk.graphml"
        # also look for a cached copy inside an attached Kaggle Dataset
        from pathlib import Path
        hits = list(C.paths()["raw"].rglob("bengaluru_metro_walk.graphml"))
        if C.paths()["env"] == "kaggle":
            hits += [Path(x) for x in C.kaggle_glob("bengaluru_metro_walk.graphml")]
        try:
            if gfile.exists():
                self.G = ox.load_graphml(gfile)
            elif hits:
                self.G = ox.load_graphml(hits[0])
            else:
                s = D.metro_stations()
                pad = 0.015
                bbox = (s["lon"].min() - pad, s["lat"].min() - pad, s["lon"].max() + pad, s["lat"].max() + pad)
                print("Downloading the OSM walking network once (5-15 min) ...")
                ox.settings.requests_timeout = 600
                self.G = ox.graph_from_bbox(bbox, network_type="walk", simplify=True)
                ox.save_graphml(self.G, gfile)
                print("Saved", gfile, "- add it to the Kaggle Dataset to skip this next time.")
            self.Gu = self.G.to_undirected()
        except Exception as exc:
            print(f"OSM walking network unavailable ({exc}); using straight line x {DETOUR_FALLBACK}.")
            self.use_osm = False
            self.G = None
        return self.G

    def _tree(self, station: str):
        if station in self._trees:
            return self._trees[station]
        import osmnx as ox
        import networkx as nx
        key = hashlib.md5(station.encode()).hexdigest()[:10]
        tfile = self.cache / f"tree_{key}_{int(self.cutoff)}.pkl"
        if tfile.exists():
            tree = pickle.loads(tfile.read_bytes())
        else:
            ent = self.entrances[self.entrances["station"] == station]
            src, snap = ox.distance.nearest_nodes(self.G, ent["lon"].values, ent["lat"].values, return_dist=True)
            # start distance = walk from the entrance to its nearest graph node
            dist0 = {}
            for n, d0 in zip(np.atleast_1d(src), np.atleast_1d(snap)):
                dist0[n] = min(dist0.get(n, np.inf), float(d0))
            tree = {}
            for n, d0 in dist0.items():
                for k, v in nx.single_source_dijkstra_path_length(self.Gu, n, cutoff=self.cutoff + 200,
                                                                   weight="length").items():
                    tree[k] = min(tree.get(k, np.inf), v + d0)
            tfile.write_bytes(pickle.dumps(tree))
        self._trees[station] = tree
        return tree

    def distances(self, stops: pd.DataFrame) -> pd.DataFrame:
        """Return station, stop_id, straight_m, walk_m for stops within the cutoff."""
        G = self._graph()
        stops = stops.reset_index(drop=True)
        if G is not None:
            import osmnx as ox
            nodes, snap = ox.distance.nearest_nodes(G, stops["stop_lon"].values, stops["stop_lat"].values,
                                                    return_dist=True)
            stops = stops.assign(_node=np.atleast_1d(nodes), _snap=np.atleast_1d(snap))
        out = []
        for _, srow in self.stations.iterrows():
            st = srow["station"]
            ent = self.entrances[self.entrances["station"] == st]
            straight = np.min([haversine(la, lo, stops["stop_lat"].values, stops["stop_lon"].values)
                               for la, lo in zip(ent["lat"], ent["lon"])], axis=0)
            keep = straight <= self.cutoff + 100
            cand = stops[keep].copy()
            cand["straight_m"] = straight[keep]
            if cand.empty:
                continue
            if G is not None:
                tree = self._tree(st)
                cand["walk_m"] = [tree.get(n, np.inf) + sd for n, sd in zip(cand["_node"], cand["_snap"])]
                self.osm_ok[st] = True
            else:
                cand["walk_m"] = cand["straight_m"] * DETOUR_FALLBACK
                self.osm_ok[st] = False
            cand["station"] = st
            out.append(cand.loc[cand["walk_m"] <= self.cutoff, ["station", "stop_id", "straight_m", "walk_m"]])
        return pd.concat(out, ignore_index=True)


# ----------------------------------------------------------------- bus-link score
def station_scores(snapshot: str = C.SNAPSHOT_BEFORE, catchment_m: float = C.CATCHMENT_M,
                   corridor_m: float = C.CORRIDOR_M, router: WalkRouter | None = None,
                   stations: pd.DataFrame | None = None, use_osm: bool = True,
                   corridor_points: pd.DataFrame | None = None, min_trip_stops: int = 1) -> pd.DataFrame:
    """Bus-network exposure of every metro station to the Yellow corridor.

    corridor_points  optional lat/lon of a different new line's stations (e.g. the Pink Line, which
                     is not in the metro GTFS); its corridor = bus stops within `corridor_m` straight line
    min_trip_stops   drop trips listing fewer stops than this (feed artefacts; 1 = keep all)

    BusTrips_s       weekday bus trips stopping within `catchment_m` walk of station s
    BusRoutes_s      distinct routes among them
    YellowLink_s     share of those trips that also stop within `corridor_m` of a new Yellow station
    YellowLinkDir_s  same, but only trips that reach the corridor *after* passing s (towards it)
    YellowLinkTrips_s  absolute number of linking trips
    Collinear_s      mean number of corridor stops visited per trip at s (route overlap with the corridor)
    near_corridor    True if s's own catchment contains corridor stops (link is trivially local)
    """
    stations = stations if stations is not None else D.metro_stations()
    g = D.load_gtfs(snapshot)
    stops = g["stops"]
    trips = D.weekday_trips(g)[["trip_id", "route_id"]]
    st = g["stop_times"].merge(trips, on="trip_id")
    if min_trip_stops > 1:
        n_stops = st.groupby("trip_id")["stop_id"].transform("size")
        st = st[n_stops >= min_trip_stops]
    router = router or WalkRouter(stations, cutoff_m=max(catchment_m, corridor_m), use_osm=use_osm)
    dist = router.distances(stops)

    if corridor_points is None:
        corridor = set(dist.loc[dist["station"].isin(C.YELLOW_NEW) & (dist["walk_m"] <= corridor_m), "stop_id"])
    else:
        dmin = np.min([haversine(la, lo, stops["stop_lat"].values, stops["stop_lon"].values)
                       for la, lo in zip(corridor_points["lat"], corridor_points["lon"])], axis=0)
        corridor = set(stops.loc[dmin <= corridor_m, "stop_id"])
    st["in_corr"] = st["stop_id"].isin(corridor)
    # per trip: corridor stops visited and the sequence range where it touches the corridor
    corr_seq = st[st["in_corr"]].groupby("trip_id")["stop_sequence"].agg(["min", "max", "nunique"])
    corr_seq.columns = ["corr_min_seq", "corr_max_seq", "corr_stops"]

    rows = []
    catch = dist[dist["walk_m"] <= catchment_m]
    for s, grp in catch.groupby("station"):
        cstops = set(grp["stop_id"])
        at = st[st["stop_id"].isin(cstops)].groupby("trip_id").agg(
            seq_min=("stop_sequence", "min"), seq_max=("stop_sequence", "max"), route_id=("route_id", "first"))
        at = at.join(corr_seq, how="left")
        linked = at["corr_stops"].notna()
        toward = linked & (at["corr_max_seq"] > at["seq_min"])
        n = len(at)
        rows.append({
            "station": s, "BusTrips": n, "BusRoutes": at["route_id"].nunique(),
            "BusStops": len(cstops),
            "YellowLinkTrips": int(linked.sum()),
            "YellowLink": linked.mean() if n else 0.0,
            "YellowLinkDir": toward.mean() if n else 0.0,
            "Collinear": at["corr_stops"].fillna(0).mean() if n else 0.0,
            "near_corridor": bool(cstops & corridor),
        })
    sc = stations[["station", "lat", "lon", "lines", "is_yellow_new"]].merge(
        pd.DataFrame(rows), on="station", how="left")
    for c in ("BusTrips", "BusRoutes", "BusStops", "YellowLinkTrips", "YellowLink", "YellowLinkDir", "Collinear"):
        sc[c] = sc[c].fillna(0)
    sc["near_corridor"] = sc["near_corridor"].fillna(False).astype(bool)

    # metro distance (stations travelled) to RV Road, from the OD fare table
    od = D.load_od()
    hops = (od[od["dest"] == C.INTERCHANGE].groupby("origin")["hops"].max())
    sc["MetroHopsToRV"] = sc["station"].map(hops)
    sc.loc[sc["station"] == C.INTERCHANGE, "MetroHopsToRV"] = 0
    sc["snapshot"] = snapshot
    sc["catchment_m"], sc["corridor_m"] = catchment_m, corridor_m
    sc["osm_walk"] = sc["station"].map(router.osm_ok).fillna(False)
    return sc


def freeze_transfer_list(scores: pd.DataFrame, k: int = C.TOP_K_TRANSFER) -> pd.DataFrame:
    """Pick the top-k bus-transfer stations by YellowLink among old stations that are
    not RV Road and not themselves next to the corridor. Writes a timestamped,
    hashed record for pre-registration. Does not look at any ridership."""
    p = C.paths()
    elig = scores[(~scores["is_yellow_new"]) & (scores["station"] != C.INTERCHANGE)
                  & (~scores["near_corridor"]) & (scores["BusTrips"] > 0)]
    top = elig.sort_values(["YellowLink", "YellowLinkTrips"], ascending=False).head(k)
    rec = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rule": f"top {k} old stations by YellowLink (snapshot {scores['snapshot'].iat[0]}, "
                f"{int(scores['catchment_m'].iat[0])} m catchment, {int(scores['corridor_m'].iat[0])} m corridor), "
                "excluding RV Road and stations whose catchment touches the corridor",
        "stations": top["station"].tolist(),
    }
    blob = json.dumps(rec, sort_keys=True).encode()
    rec["sha256"] = hashlib.sha256(blob).hexdigest()
    (p["out"] / "frozen_transfer_stations.json").write_text(json.dumps(rec, indent=2))
    top.to_csv(p["tab"] / "frozen_transfer_stations.csv", index=False)
    return top


# ----------------------------------------------------------------- supply over snapshots (pandas)
def supply_panel(snapshots: list[str] | None = None, radius_m: float = C.CATCHMENT_M,
                 stations: pd.DataFrame | None = None, router: WalkRouter | None = None) -> pd.DataFrame:
    """Weekday bus trips and routes within `radius_m` walk of each metro station, per snapshot."""
    stations = stations if stations is not None else D.metro_stations()
    router = router or WalkRouter(stations, cutoff_m=C.CORRIDOR_M)
    rows = []
    for date in snapshots or list(C.BMTC_SNAPSHOTS):
        if not D.gtfs_path(date).exists():
            print("skip missing snapshot", date)
            continue
        g = D.load_gtfs(date)
        trips = D.weekday_trips(g)[["trip_id", "route_id"]]
        st = g["stop_times"].merge(trips, on="trip_id")
        dist = router.distances(g["stops"])
        catch = dist[dist["walk_m"] <= radius_m][["station", "stop_id"]]
        m = st.merge(catch, on="stop_id")
        agg = m.groupby("station").agg(trips=("trip_id", "nunique"), routes=("route_id", "nunique"))
        agg = agg.reindex(stations["station"]).fillna(0).reset_index()
        agg["snapshot"] = date
        agg["total_trips_network"] = trips["trip_id"].nunique()
        rows.append(agg)
        print("supply", date, "network trips", agg["total_trips_network"].iat[0])
    return pd.concat(rows, ignore_index=True)


def route_diff(before: str = C.SNAPSHOT_BEFORE, after: str = C.SNAPSHOT_AFTER,
               radius_m: float = C.CORRIDOR_M) -> pd.DataFrame:
    """Routes serving the new Yellow stations that were added, removed or changed trip counts."""
    stations = D.metro_stations()
    router = WalkRouter(stations, cutoff_m=C.CORRIDOR_M)
    res = {}
    for tag, date in (("before", before), ("after", after)):
        g = D.load_gtfs(date)
        trips = D.weekday_trips(g)[["trip_id", "route_id"]]
        rshort = g["routes"].set_index("route_id")["route_short_name"]
        st = g["stop_times"].merge(trips, on="trip_id")
        dist = router.distances(g["stops"])
        near = dist[dist["station"].isin(C.YELLOW_NEW) & (dist["walk_m"] <= radius_m)]
        m = st.merge(near[["station", "stop_id"]], on="stop_id")
        m["route"] = m["route_id"].map(rshort).fillna(m["route_id"])
        res[tag] = m.groupby("route")["trip_id"].nunique().rename(f"trips_{tag}")
    out = pd.concat(res.values(), axis=1).fillna(0)
    out["change"] = out["trips_after"] - out["trips_before"]
    out["status"] = np.select([out["trips_before"] == 0, out["trips_after"] == 0], ["added", "removed"], "kept")
    out["is_feeder_MF"] = out.index.str.upper().str.startswith("MF")
    return out.sort_values("change", ascending=False).reset_index()


# ----------------------------------------------------------------- Spark version (big-data path)
def spark_station_stop_pairs(spark, stations: pd.DataFrame, radius_m: float = C.CATCHMENT_M,
                             snapshots: list[str] | None = None):
    """Straight-line station-to-stop pairs within radius, computed in Spark for every
    snapshot (stations are broadcast; stops come from HDFS)."""
    from pyspark.sql import functions as F
    from .env import hdfs_path
    stops = spark.read.parquet(hdfs_path("gtfs/stops"))
    if snapshots:
        stops = stops.where(F.col("snapshot").isin(snapshots))
    stops = stops.select("snapshot", "stop_id", F.col("stop_lat").cast("double").alias("slat"),
                         F.col("stop_lon").cast("double").alias("slon"))
    sdf = F.broadcast(spark.createDataFrame(stations[["station", "lat", "lon"]]))
    j = stops.crossJoin(sdf)
    rad = F.lit(np.pi / 180)
    a = (F.sin((F.col("slat") - F.col("lat")) * rad / 2) ** 2
         + F.cos(F.col("lat") * rad) * F.cos(F.col("slat") * rad)
         * F.sin((F.col("slon") - F.col("lon")) * rad / 2) ** 2)
    j = j.withColumn("dist_m", 2 * F.lit(EARTH_R) * F.asin(F.sqrt(a)))
    return j.where(F.col("dist_m") <= radius_m).select("snapshot", "station", "stop_id", "dist_m")


def spark_supply(spark, stations: pd.DataFrame, radius_m: float = C.CATCHMENT_M,
                 snapshots: list[str] | None = None):
    """Spark job: weekday trips and routes within radius of each metro station per snapshot."""
    from pyspark.sql import functions as F
    from .env import hdfs_path
    pairs = spark_station_stop_pairs(spark, stations, radius_m, snapshots)
    st = spark.read.parquet(hdfs_path("gtfs/stop_times")).select("snapshot", "trip_id", "stop_id")
    trips = spark.read.parquet(hdfs_path("gtfs/trips")).select("snapshot", "trip_id", "route_id", "service_id")
    try:
        cal = (spark.read.parquet(hdfs_path("gtfs/calendar"))
               .where(F.col("wednesday") == "1").select("snapshot", "service_id"))
        trips = trips.join(cal, ["snapshot", "service_id"], "left_semi")
    except Exception:
        pass
    if snapshots:
        st = st.where(F.col("snapshot").isin(snapshots))
        trips = trips.where(F.col("snapshot").isin(snapshots))
    m = st.join(pairs, ["snapshot", "stop_id"]).join(trips, ["snapshot", "trip_id"])
    return m.groupBy("snapshot", "station").agg(F.countDistinct("trip_id").alias("trips"),
                                                F.countDistinct("route_id").alias("routes"))
