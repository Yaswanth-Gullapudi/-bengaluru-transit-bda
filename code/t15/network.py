"""Descriptive network analytics promised in the original abstract (notebook 09).

Data quality and cleaning, route distribution, high-frequency routes, commonly shared
stops, route connectivity, stop accessibility to metro, metro demand patterns by time,
network size over time, and a CSV-vs-Parquet storage comparison. Everything runs in
Spark (Spark SQL / DataFrame API) on the HDFS copy written by notebook 00; on a laptop
without HDFS it falls back to local Parquet built from the raw files.
"""
from __future__ import annotations

import os
import shutil
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from . import data as D

BBOX = (12.3, 13.7, 76.9, 78.3)          # BMTC service area incl. Magadi, Chikkaballapur, Hosur; catches bad coordinates
EARTH_R = 6_371_000.0
GTFS_TABLES = ("stops", "routes", "trips", "stop_times", "calendar")


# ----------------------------------------------------------------------------- loading
def _use_hdfs() -> bool:
    return C.paths()["env"] != "local"


def _local_parquet(name: str, make) -> str:
    """Build a local Parquet file once with pandas (Spark on Windows cannot write files)."""
    d = C.paths()["cache"] / "net"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{name}.parquet"
    if not f.exists():
        make().to_parquet(f, index=False)
    return str(f) if os.name == "nt" else f"file://{f}"     # local file, not the HDFS default FS


def gtfs(spark, table: str, snapshot: str):
    """One GTFS table for one snapshot as a Spark DataFrame (all columns as strings)."""
    from pyspark.sql import functions as F
    if _use_hdfs():
        from .env import hdfs_path
        try:
            return (spark.read.parquet(hdfs_path(f"gtfs/{table}"))
                    .where(F.col("snapshot") == snapshot))
        except Exception as exc:                      # fall back to the raw zip
            print(f"HDFS read of gtfs/{table} failed ({exc.__class__.__name__}); using raw zip")

    def make():
        z = zipfile.ZipFile(D.gtfs_path(snapshot))
        return pd.read_csv(z.open(f"{table}.txt"), dtype=str)
    return spark.read.parquet(_local_parquet(f"{table}_{snapshot}", make)).withColumn("snapshot", F.lit(snapshot))


def gtfs_snapshots(spark) -> list[str]:
    """Snapshots available to this session (all 26 on Kaggle/HDFS, fewer on a laptop)."""
    if _use_hdfs():
        try:
            from .env import hdfs_path
            return sorted(r.snapshot for r in spark.read.parquet(hdfs_path("gtfs/routes"))
                          .select("snapshot").distinct().collect())
        except Exception:
            pass
    return [s for s in C.BMTC_SNAPSHOTS if D.gtfs_path(s).exists()]


def metro(spark, key: str):
    """Metro ridership table ('entries', 'exits', 'od') as a Spark DataFrame."""
    if _use_hdfs():
        from .env import hdfs_path
        try:
            return spark.read.parquet(hdfs_path(f"metro/{key}"))
        except Exception as exc:
            print(f"HDFS read of metro/{key} failed ({exc.__class__.__name__}); using local file")
    make = {"entries": lambda: D.load_station_hourly("entries"),
            "exits": lambda: D.load_station_hourly("exits"),
            "od": D.load_od}[key]
    return spark.read.parquet(_local_parquet(f"metro_{key}", make))


def _hav(lat1, lon1, lat2, lon2):
    from pyspark.sql import functions as F
    rad = F.lit(np.pi / 180)
    a = (F.sin((lat2 - lat1) * rad / 2) ** 2
         + F.cos(lat1 * rad) * F.cos(lat2 * rad) * F.sin((lon2 - lon1) * rad / 2) ** 2)
    return 2 * F.lit(EARTH_R) * F.asin(F.sqrt(a))


# ----------------------------------------------------------------------------- 1. data quality
def data_quality(spark, snapshot: str) -> tuple[pd.DataFrame, dict]:
    """Checks on every raw table; returns (report, cleaned Spark DataFrames).

    Cleaning rules: drop exact duplicates; drop stops without coordinates or outside the
    Bengaluru bounding box; keep trips whose route exists and that run on a weekday
    (Wednesday service); keep stop_times whose trip and stop survive.
    """
    from pyspark.sql import functions as F
    T = {t: gtfs(spark, t, snapshot).drop("snapshot") for t in GTFS_TABLES}
    rows = []

    def add(table, check, n, action):
        if check != "raw rows" and int(n) == 0:
            action = "none found"
        rows.append({"table": table, "check": check, "rows_affected": int(n), "action": action})

    for t, df in T.items():
        n = df.count()
        add(t, "raw rows", n, "-")
        add(t, "exact duplicate rows", n - df.dropDuplicates().count(), "dropped")

    s = T["stops"].withColumn("lat", F.col("stop_lat").cast("double")).withColumn("lon", F.col("stop_lon").cast("double"))
    add("stops", "missing coordinates", s.where(F.col("lat").isNull() | F.col("lon").isNull()).count(), "dropped")
    lat0, lat1, lon0, lon1 = BBOX
    outside = s.where(F.col("lat").isNotNull() & ~(F.col("lat").between(lat0, lat1) & F.col("lon").between(lon0, lon1)))
    add("stops", "outside BMTC service area (bad coordinates)", outside.count(), "dropped")
    add("stops", "duplicate stop_id", s.count() - s.select("stop_id").distinct().count(), "first kept")
    add("stops", "missing stop_name", s.where(F.col("stop_name").isNull()).count(), "kept, named by id")
    stops = (s.dropDuplicates(["stop_id"]).where(F.col("lat").between(lat0, lat1) & F.col("lon").between(lon0, lon1))
             .withColumn("stop_name", F.coalesce(F.col("stop_name"), F.col("stop_id"))))

    r = T["routes"].dropDuplicates(["route_id"])
    add("routes", "missing route_short_name", r.where(F.col("route_short_name").isNull()).count(), "route_id used")
    routes = r.withColumn("route", F.coalesce(F.col("route_short_name"), F.col("route_id")))

    tr = T["trips"].dropDuplicates(["trip_id"])
    add("trips", "route_id not in routes", tr.join(routes, "route_id", "left_anti").count(), "dropped")
    cal = T["calendar"].dropDuplicates()
    wk = cal.where(F.col("wednesday") == "1").select("service_id")
    n_wk = wk.count()
    trips = tr.join(routes.select("route_id", "route"), "route_id")
    trips_wk = trips.join(wk, "service_id", "left_semi") if n_wk else trips
    add("trips", "not running on a weekday (Wednesday)", trips.count() - trips_wk.count(), "excluded from weekday analysis")

    st = (T["stop_times"].dropDuplicates()
          .withColumn("seq", F.col("stop_sequence").cast("int"))
          .withColumn("hour", F.split(F.col("departure_time"), ":").getItem(0).cast("int")))
    add("stop_times", "missing stop_id or time", st.where(F.col("stop_id").isNull() | F.col("departure_time").isNull()).count(), "dropped")
    add("stop_times", "stop_id not in cleaned stops", st.join(stops.select("stop_id"), "stop_id", "left_anti").count(), "dropped")
    add("stop_times", "trip_id not in trips", st.join(tr.select("trip_id"), "trip_id", "left_anti").count(), "dropped")
    add("stop_times", "times past midnight (hour 24+)", st.where(F.col("hour") >= 24).count(), "kept (valid GTFS), hour mod 24")
    add("stop_times", "duplicate (trip_id, stop_sequence)",
        st.count() - st.dropDuplicates(["trip_id", "seq"]).count(), "first kept")
    nstops = st.groupBy("trip_id").count()
    add("trips", "only 1-2 stops listed (incomplete stop list in feed)", nstops.where(F.col("count") <= 2).count(),
        "kept in trip counts; excluded from length and stops-per-trip statistics")
    stop_times = (st.where(F.col("stop_id").isNotNull() & F.col("departure_time").isNotNull())
                  .dropDuplicates(["trip_id", "seq"])
                  .join(stops.select("stop_id"), "stop_id", "left_semi")
                  .join(trips.select("trip_id"), "trip_id", "left_semi")
                  .withColumn("hour", F.col("hour") % 24))

    for key in ("entries", "exits"):
        m = metro(spark, key)
        n = m.count()
        add(f"metro {key}", "raw rows", n, "-")
        add(f"metro {key}", "duplicate station-date-hour",
            n - m.dropDuplicates(["station", "date", "hour"]).count(), "summed")
        add(f"metro {key}", "missing values", m.where(F.col(m.columns[-1]).isNull()).count(), "dropped")
        add(f"metro {key}", "negative counts", m.where(F.col(m.columns[-1]) < 0).count(), "set to 0")
    od = metro(spark, "od")
    add("metro od", "raw rows", od.count(), "-")
    add("metro od", "origin equals destination (entry and exit at same station)", od.where(F.col("origin") == F.col("dest")).count(), "excluded from OD analysis")

    report = pd.DataFrame(rows)
    report.insert(0, "snapshot", snapshot)
    clean = {"stops": stops.cache(), "routes": routes.cache(), "trips": trips.cache(),
             "trips_wk": trips_wk.cache(), "stop_times": stop_times.cache()}
    return report, clean


# ----------------------------------------------------------------------------- 2-3. routes
def route_stats(spark, clean: dict) -> pd.DataFrame:
    """Per route: weekday trips, stops per trip, route length (km), service span (h)."""
    from pyspark.sql import Window
    from pyspark.sql import functions as F
    st = clean["stop_times"].join(clean["trips_wk"].select("trip_id", "route_id", "route"), "trip_id")
    st = st.join(clean["stops"].select("stop_id", "lat", "lon"), "stop_id")
    w = Window.partitionBy("trip_id").orderBy("seq")
    st = st.withColumn("plat", F.lag("lat").over(w)).withColumn("plon", F.lag("lon").over(w))
    st = st.withColumn("seg_m", F.when(F.col("plat").isNull(), 0.0).otherwise(_hav(F.col("plat"), F.col("plon"), F.col("lat"), F.col("lon"))))
    per_trip = st.groupBy("route_id", "route", "trip_id").agg(
        F.count("*").alias("stops"), (F.sum("seg_m") / 1000).alias("km"),
        F.min("hour").alias("first_h"), F.max("hour").alias("last_h"))
    full = F.col("stops") >= 3          # trips with 1-2 listed stops are feed artefacts (see data_quality)
    per_route = per_trip.groupBy("route_id", "route").agg(
        F.countDistinct("trip_id").alias("weekday_trips"),
        F.expr("percentile_approx(CASE WHEN stops >= 3 THEN stops END, 0.5)").alias("stops_per_trip"),
        F.expr("percentile_approx(CASE WHEN stops >= 3 THEN km END, 0.5)").alias("length_km"),
        F.sum(F.when(full, 0).otherwise(1)).alias("short_trips"),
        F.min("first_h").alias("first_hour"), F.max("last_h").alias("last_hour"))
    out = per_route.toPandas()
    out["span_h"] = out["last_hour"] - out["first_hour"] + 1
    names = clean["routes"].select("route_id", "route_long_name").toPandas()
    return out.merge(names, on="route_id", how="left").sort_values("weekday_trips", ascending=False)


# ----------------------------------------------------------------------------- 4. shared stops
def shared_stops(spark, clean: dict) -> pd.DataFrame:
    """Stops grouped by name (platforms of one place share a name): routes and weekday trips."""
    from pyspark.sql import functions as F
    st = (clean["stop_times"].select("trip_id", "stop_id")
          .join(clean["trips_wk"].select("trip_id", "route_id"), "trip_id")
          .join(clean["stops"].select("stop_id", "stop_name", "lat", "lon"), "stop_id"))
    g = st.groupBy("stop_name").agg(F.countDistinct("route_id").alias("routes"),
                                    F.countDistinct("trip_id").alias("weekday_trips"),
                                    F.countDistinct("stop_id").alias("platforms"),
                                    F.avg("lat").alias("lat"), F.avg("lon").alias("lon"))
    return g.toPandas().sort_values("routes", ascending=False)


# ----------------------------------------------------------------------------- 5. connectivity
def connectivity(spark, clean: dict, stations: pd.DataFrame, radius_m: float = 400) -> dict:
    """Stop-route degree, one-transfer route graph, and stop access to metro stations."""
    from pyspark.sql import functions as F
    rs = (clean["stop_times"].select("trip_id", "stop_id")
          .join(clean["trips_wk"].select("trip_id", "route_id"), "trip_id")
          .select("stop_id", "route_id").distinct().cache())
    stop_deg = rs.groupBy("stop_id").agg(F.count("*").alias("routes")).toPandas()
    a, b = rs.alias("a"), rs.alias("b")
    pairs = (a.join(b, (F.col("a.stop_id") == F.col("b.stop_id")) & (F.col("a.route_id") < F.col("b.route_id")))
             .select(F.col("a.route_id").alias("r1"), F.col("b.route_id").alias("r2")).distinct().cache())
    n_routes = rs.select("route_id").distinct().count()
    n_pairs = pairs.count()
    deg = (pairs.select(F.col("r1").alias("route_id")).union(pairs.select(F.col("r2").alias("route_id")))
           .groupBy("route_id").count().withColumnRenamed("count", "routes_one_transfer").toPandas())
    deg = deg.merge(clean["routes"].select("route_id", "route").toPandas(), on="route_id", how="left")

    sdf = F.broadcast(spark.createDataFrame(stations[["station", "lat", "lon"]]
                                            .rename(columns={"lat": "mlat", "lon": "mlon"})))
    served = clean["stops"].join(rs.select("stop_id").distinct(), "stop_id", "left_semi")
    near = (served.crossJoin(sdf).withColumn("d", _hav(F.col("lat"), F.col("lon"), F.col("mlat"), F.col("mlon")))
            .groupBy("stop_id").agg(F.min("d").alias("metro_m")))
    near_pd = near.toPandas()
    summary = {
        "served_stops": int(served.count()),
        "routes": n_routes,
        "route_pairs_sharing_a_stop": n_pairs,
        "network_density": n_pairs / (n_routes * (n_routes - 1) / 2) if n_routes > 1 else np.nan,
        "median_routes_per_stop": float(stop_deg.routes.median()),
        "share_stops_single_route": float((stop_deg.routes == 1).mean()),
        "median_routes_one_transfer": float(deg.routes_one_transfer.median()) if len(deg) else np.nan,
        f"share_stops_within_{int(radius_m)}m_of_metro": float((near_pd.metro_m <= radius_m).mean()),
        "share_stops_within_800m_of_metro": float((near_pd.metro_m <= 800).mean()),
        "median_stop_to_metro_km": float(near_pd.metro_m.median() / 1000),
    }
    rs.unpersist(); pairs.unpersist()
    return {"summary": summary, "stop_degree": stop_deg, "route_degree": deg.sort_values("routes_one_transfer", ascending=False),
            "stop_to_metro": near_pd}


# ----------------------------------------------------------------------------- 6. metro demand
def metro_demand(spark) -> dict:
    """Hourly profile, busiest stations, peak share, top OD pairs, daily ridership by line."""
    from pyspark.sql import functions as F
    e = metro(spark, "entries")
    val = e.columns[-1] if "entries" not in e.columns else "entries"
    e = e.withColumnRenamed(val, "entries") if val != "entries" else e
    e = e.withColumn("dt", F.to_date("date")).withColumn("dow", F.dayofweek("dt"))
    e = e.withColumn("daytype", F.when(F.col("dow").isin(1, 7), "weekend").otherwise("weekday"))
    e = e.withColumn("period", F.when(F.col("date") < "2025-08-11", "1-10 Aug (before Yellow)")
                     .when(F.col("date") <= "2025-08-18", "11-18 Aug (after)").otherwise("September"))
    e.createOrReplaceTempView("entries")
    hourly = spark.sql("""
        SELECT period, daytype, hour, SUM(entries) / COUNT(DISTINCT date) AS avg_entries
        FROM entries GROUP BY period, daytype, hour ORDER BY period, daytype, hour""").toPandas()
    busiest = spark.sql("""
        SELECT station, SUM(entries) / COUNT(DISTINCT date) AS avg_daily_entries
        FROM entries WHERE period = '1-10 Aug (before Yellow)' AND daytype = 'weekday'
        GROUP BY station ORDER BY avg_daily_entries DESC""").toPandas()
    peak = spark.sql("""
        SELECT daytype,
               SUM(CASE WHEN hour BETWEEN 8 AND 10 THEN entries END) / SUM(entries) AS am_peak_share,
               SUM(CASE WHEN hour BETWEEN 17 AND 19 THEN entries END) / SUM(entries) AS pm_peak_share
        FROM entries GROUP BY daytype""").toPandas()
    st = D.metro_stations()[["station", "lines"]]
    spark.createDataFrame(st).createOrReplaceTempView("stations")
    by_line = spark.sql("""
        SELECT e.date, s.lines AS line, SUM(e.entries) AS entries
        FROM entries e JOIN stations s ON e.station = s.station
        GROUP BY e.date, s.lines ORDER BY e.date""").toPandas()
    od = metro(spark, "od")
    od.createOrReplaceTempView("od")
    top_od = spark.sql("""
        SELECT origin, dest, SUM(trips) / COUNT(DISTINCT date) AS avg_daily_trips
        FROM od WHERE date < '2025-08-11' AND origin <> dest
        GROUP BY origin, dest ORDER BY avg_daily_trips DESC LIMIT 20""").toPandas()
    return {"hourly": hourly, "busiest": busiest, "peak": peak, "by_line": by_line, "top_od": top_od}


# ----------------------------------------------------------------------------- 7. network over time
def network_over_time(spark, snapshots: list[str]) -> pd.DataFrame:
    """Stops, routes and weekday trips in every available snapshot (one Spark job per table)."""
    from pyspark.sql import functions as F
    rows = []
    for s in snapshots:
        trips = gtfs(spark, "trips", s)
        cal = gtfs(spark, "calendar", s).where(F.col("wednesday") == "1").select("service_id")
        wk = trips.join(cal, "service_id", "left_semi")
        rows.append({"snapshot": s,
                     "stops": gtfs(spark, "stops", s).select("stop_id").distinct().count(),
                     "routes": gtfs(spark, "routes", s).select("route_id").distinct().count(),
                     "weekday_trips": wk.select("trip_id").distinct().count()})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- 8. storage format
def _dir_size(path: str) -> int:
    """Size in bytes of a local or HDFS path."""
    if path.startswith("hdfs://"):
        import subprocess
        out = subprocess.run(["hdfs", "dfs", "-du", "-s", path], capture_output=True, text=True).stdout.split()
        return int(out[0]) if out else 0
    p = Path(path.replace("file://", ""))
    return p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def storage_benchmark(spark, snapshot: str, repeats: int = 3) -> pd.DataFrame:
    """CSV (the format named in the proposal) vs Parquet for stop_times: size and query time."""
    from pyspark.sql import functions as F
    st = gtfs(spark, "stop_times", snapshot).drop("snapshot")
    if _use_hdfs():
        from .env import hdfs_path
        base = hdfs_path(f"bench/{snapshot}")
        st.write.mode("overwrite").option("header", True).csv(f"{base}/csv")
        st.write.mode("overwrite").parquet(f"{base}/parquet")
        paths = {"CSV": f"{base}/csv", "Parquet": f"{base}/parquet"}
    else:                                   # laptop: write with pandas, read with Spark
        d = C.paths()["cache"] / "bench"
        shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
        pdf = st.toPandas()
        pdf.to_csv(d / "stop_times.csv", index=False)
        pdf.to_parquet(d / "stop_times.parquet", index=False)
        paths = {"CSV": str(d / "stop_times.csv"), "Parquet": str(d / "stop_times.parquet")}
    rows = []
    for fmt, p in paths.items():
        def read():
            return (spark.read.option("header", True).csv(p) if fmt == "CSV" else spark.read.parquet(p))
        for task, fn in (("count rows", lambda df: df.count()),
                         ("trips per stop (group by)", lambda df: df.groupBy("stop_id").agg(F.countDistinct("trip_id")).count()),
                         ("read one column", lambda df: df.select("stop_id").distinct().count())):
            ts = []
            for _ in range(repeats):
                t0 = time.perf_counter(); fn(read()); ts.append(time.perf_counter() - t0)
            rows.append({"format": fmt, "task": task, "seconds_median": float(np.median(ts))})
        rows.append({"format": fmt, "task": "size on disk (MB)", "seconds_median": _dir_size(p) / 1e6})
    return pd.DataFrame(rows)
