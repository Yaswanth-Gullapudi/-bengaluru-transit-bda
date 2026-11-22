"""Spark scaling experiments and a pandas baseline on the same job.

Job = for N GTFS snapshots: station-to-stop pairs within 400 m (straight line),
join with stop_times and trips, count distinct weekday trips and routes per
metro station per snapshot; plus the OD band aggregation of the metro table.
Data size grows with N (real snapshots, not copies): 1, 5, 10, 20, 26.
"""
from __future__ import annotations

import gc
import statistics
import time

import numpy as np
import pandas as pd

from . import bus as B
from . import config as C
from . import data as D


def spark_job(spark, stations: pd.DataFrame, snapshots: list[str]) -> int:
    from pyspark.sql import functions as F
    from .env import hdfs_path
    sup = B.spark_supply(spark, stations, C.CATCHMENT_M, snapshots)
    n1 = sup.count()
    od = spark.read.parquet(hdfs_path("metro/od"))
    band = (F.when(F.col("hour").between(7, 10), "am_peak").when(F.col("hour").between(11, 15), "midday")
            .when(F.col("hour").between(16, 20), "pm_peak").otherwise("other"))
    n2 = od.withColumn("band", band).groupBy("origin", "dest", "date", "band").agg(F.sum("trips")).count()
    return n1 + n2


def pandas_job(stations: pd.DataFrame, snapshots: list[str]) -> int:
    out = 0
    frames = []
    for date in snapshots:
        g = D.load_gtfs(date)
        trips = D.weekday_trips(g)[["trip_id", "route_id"]]
        stops = g["stops"]
        pairs = []
        for _, s in stations.iterrows():
            d = B.haversine(s["lat"], s["lon"], stops["stop_lat"].values, stops["stop_lon"].values)
            pairs.append(pd.DataFrame({"station": s["station"], "stop_id": stops["stop_id"].values[d <= C.CATCHMENT_M]}))
        pairs = pd.concat(pairs)
        m = g["stop_times"].merge(pairs, on="stop_id").merge(trips, on="trip_id")
        frames.append(m.groupby("station").agg(trips=("trip_id", "nunique"), routes=("route_id", "nunique")))
    out += sum(len(f) for f in frames)
    od = D.load_od()
    od["band"] = od["hour"].map(C.band_of)
    out += len(od.groupby(["origin", "dest", "date", "band"])["trips"].sum())
    return out


def input_rows(spark, snapshots: list[str]) -> int:
    from pyspark.sql import functions as F
    from .env import hdfs_path
    return spark.read.parquet(hdfs_path("gtfs/stop_times")).where(F.col("snapshot").isin(snapshots)).count()


def run(sizes=(1, 5, 10, 20, 26), cores=(1, 2, 4), repeats: int = 3, pandas_max: int = 26,
        memory: str = "20g") -> pd.DataFrame:
    """Time the job for every (cores, size). Starts a fresh Spark session per core count."""
    from .env import spark_session
    stations = D.metro_stations()
    snaps = list(C.BMTC_SNAPSHOTS)
    rows = []
    for c in cores:
        spark = spark_session(cores=c, memory=memory, app=f"scaling-{c}")
        for n in sizes:
            sel = snaps[-n:]
            spark_job(spark, stations, sel[:1])        # warm-up (JIT, file listing cache)
            times = []
            for _ in range(repeats):
                t0 = time.perf_counter()
                spark_job(spark, stations, sel)
                times.append(time.perf_counter() - t0)
            rows.append({"engine": "spark", "cores": c, "snapshots": n, "stop_times_rows": input_rows(spark, sel),
                         "seconds_median": statistics.median(times), "seconds_all": times})
            print(rows[-1])
        spark.stop()
    for n in sizes:
        if n > pandas_max:
            continue
        sel = snaps[-n:]
        times, peak = [], np.nan
        for r in range(repeats):
            gc.collect()
            t0 = time.perf_counter()
            try:
                pandas_job(stations, sel)
                times.append(time.perf_counter() - t0)
            except MemoryError:
                times.append(np.inf)
            try:
                import psutil
                peak = psutil.Process().memory_info().rss / 1e9   # resident memory after the job
            except ImportError:
                pass
        rows.append({"engine": "pandas", "cores": 1, "snapshots": n, "stop_times_rows": np.nan,
                     "seconds_median": statistics.median(times), "seconds_all": times, "peak_mem_gb": peak})
        print(rows[-1])
    df = pd.DataFrame(rows)
    # speed-up relative to 1 core at the same size (strong scaling)
    base = df[(df["engine"] == "spark") & (df["cores"] == 1)].set_index("snapshots")["seconds_median"]
    df["speedup_vs_1core"] = df.apply(lambda r: base.get(r["snapshots"], np.nan) / r["seconds_median"]
                                      if r["engine"] == "spark" else np.nan, axis=1)
    return df
