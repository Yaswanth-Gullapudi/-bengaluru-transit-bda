# %% [markdown]
# # 00 · Setup, data download and HDFS ingest
# **Team 15: Did the bus network decide who lost metro riders when the Yellow Line opened?**
#
# Run this notebook **once** on Kaggle (Settings → Internet **on**, Accelerator **None**; this is CPU work).
# It:
# 1. downloads every open dataset into `/kaggle/working/data_raw/`
#    * BMRCL hourly station entries/exits (Aug + Sep 2025) and hourly station-pair flows (1–18 Aug 2025)
#    * BMRCL GTFS (station coordinates, entrances, lines)
#    * all 26 BMTC GTFS snapshots (Jan 2024 → Nov 2026)
#    * RAS-PT polling-booth population + 2018 bus-stop access (29 assembly constituencies)
# 2. starts a single-node **HDFS** and **Spark**, and writes every table to HDFS as parquet
#    (GTFS partitioned by snapshot date)
# 3. builds the OpenStreetMap walking network once (skipped if the cached GraphML is attached)
#
# **After it finishes:** *Save Version → Save & Run All*, then from the notebook's **Output** tab
# click **New Dataset** and name it `t15-data`. Every other notebook attaches `t15-data` + `t15-code`.
#
# OpenCity ward files (bus stops and routes by ward) cannot be downloaded by script.
# Download them in a browser and add them to `t15-data` in a folder named `ward/`.

# %%
SETUP

# %% [markdown]
# ## 1 · Download everything

# %%
raw = D.download_all()            # ~1.5 GB, 5-10 min; skips files that already exist
!du -sh {raw}/*

# %%
# Quick look at the metro tables
ent, exi, od = D.load_station_hourly("entries"), D.load_station_hourly("exits"), D.load_od()
print("entries", ent.shape, ent.date.min(), "->", ent.date.max(), ent.date.nunique(), "days")
print("exits  ", exi.shape, exi.date.min(), "->", exi.date.max())
print("OD     ", od.shape, od.date.min(), "->", od.date.max(), "| trips", od.trips.sum())
st = D.metro_stations()
print(st.lines.value_counts())
st.head()

# %% [markdown]
# ## 2 · Start HDFS + Spark and ingest

# %%
from t15 import env
spark = env.start(cores=4, memory="20g")
!hdfs dfsadmin -report | head -20

# %%
import time
t0 = time.time()
D.ingest_to_hdfs(spark)           # metro tables + 26 GTFS snapshots x 5 tables
print(f"ingest took {time.time()-t0:.0f}s")
!hdfs dfs -du -h /t15
!hdfs dfs -ls /t15/gtfs/stop_times | head

# %%
# Sanity check with Spark SQL straight from HDFS
spark.read.parquet(env.hdfs_path("gtfs/stop_times")).createOrReplaceTempView("stop_times")
spark.read.parquet(env.hdfs_path("metro/od")).createOrReplaceTempView("od")
spark.sql("""SELECT snapshot, COUNT(*) AS stop_time_rows, COUNT(DISTINCT trip_id) AS trips
             FROM stop_times GROUP BY snapshot ORDER BY snapshot""").show(30)
spark.sql("SELECT date, SUM(trips) AS trips FROM od GROUP BY date ORDER BY date").show(20)

# %% [markdown]
# ## 3 · OpenStreetMap walking network (once)
# One graph for the whole metro area. ~5-15 min the first time; afterwards it is read from
# the cached GraphML (copy `outputs/cache/walk/bengaluru_metro_walk.graphml` into `t15-data`).

# %%
r = PL.router()
G = r._graph()
print(G is not None and f"{G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
!cp -r /kaggle/working/outputs/cache/walk/bengaluru_metro_walk.graphml /kaggle/working/data_raw/ 2>/dev/null; ls -la /kaggle/working/data_raw

# %%
spark.stop()
