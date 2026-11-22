# %% [markdown]
# # 09 · Bengaluru public transport network analytics (the BDA framework from the proposal)
# This notebook delivers the descriptive analyses promised in the original abstract, all in **Spark on HDFS**:
# 1. **Data quality and cleaning:** duplicates, missing values, invalid coordinates, broken references
# 2. **Route distribution:** route length, stops per trip, trips per route, service span
# 3. **High-frequency routes**
# 4. **Commonly shared stops** (hubs served by the most routes)
# 5. **Route connectivity** (routes reachable with one transfer) and **stop accessibility to metro**
# 6. **Metro ridership demand patterns by time** (hourly profile, peaks, busiest stations, top OD pairs, by line)
# 7. **Network size over time** across all GTFS snapshots
# 8. **Storage format:** CSV (the format in the proposal) vs Parquet, size and query speed
#
# Main snapshot: 4 Aug 2025 (the last before the Yellow Line opened).

# %%
SETUP

# %%
from t15 import env, network as N
import pandas as pd, numpy as np, matplotlib.pyplot as plt
spark = env.start(cores=4, memory="20g")
# HDFS is empty in every new Kaggle session: load the raw data written by notebook 00 (about 4 minutes)
missing = [s for s in C.BMTC_SNAPSHOTS if not D.hdfs_has(spark, f"gtfs/stop_times/snapshot={s}")]
if missing or not D.hdfs_has(spark, "metro/entries"):
    D.ingest_to_hdfs(spark, snapshots=missing)
SNAP = C.SNAPSHOT_BEFORE
snaps = N.gtfs_snapshots(spark)
print("main snapshot", SNAP, "| snapshots available:", len(snaps))

# %% [markdown]
# ## 1 · Data quality and cleaning (Spark DataFrame API)

# %%
quality, clean = N.data_quality(spark, SNAP)
PL.save_table(quality, "network_data_quality.csv")
quality

# %%
print({k: v.count() for k, v in clean.items()})   # rows kept after cleaning

# %% [markdown]
# ## 2–3 · Route distribution and high-frequency routes

# %%
routes = N.route_stats(spark, clean)
PL.save_table(routes, "network_route_stats.csv")
print(routes[["weekday_trips", "stops_per_trip", "length_km", "span_h", "short_trips"]].describe().round(1))
routes.head(20)[["route", "route_long_name", "weekday_trips", "stops_per_trip", "length_km", "first_hour", "last_hour"]]

# %%
fig, ax = plt.subplots(1, 3, figsize=(15, 3.8))
rs = routes.dropna(subset=["length_km"])
ax[0].hist(rs.length_km.clip(upper=60), bins=40, color="#1f6fb2"); ax[0].set_title("Route length (km, median trip)"); ax[0].set_xlabel("km (last bar = 60 or more)")
ax[1].hist(rs.stops_per_trip, bins=40, color="#1f6fb2"); ax[1].set_title("Stops per trip (trips with 3+ stops)"); ax[1].set_xlabel("stops")
ax[2].hist(routes.weekday_trips.clip(upper=200), bins=40, color="#1f6fb2"); ax[2].set_title("Weekday trips per route"); ax[2].set_xlabel("trips (last bar = 200 or more)")
for a in ax: a.set_ylabel("routes")
fig.suptitle(f"BMTC route distribution, {SNAP}: {len(routes):,} routes; {len(rs):,} with full stop lists")
PL.save_fig(fig, "fig13_route_distribution.png")

# %% [markdown]
# ## 4 · Commonly shared stops

# %%
stops = N.shared_stops(spark, clean)
PL.save_table(stops, "network_shared_stops.csv")
stops.head(20)

# %%
fig, ax = plt.subplots(1, 2, figsize=(15, 6))
t = routes.head(20).iloc[::-1]
ax[0].barh(t.route.astype(str), t.weekday_trips, color="#1f6fb2"); ax[0].set_title("Top 20 routes by weekday trips")
s20 = stops.head(20).iloc[::-1]
ax[1].barh(s20.stop_name, s20.routes, color="#d9a400"); ax[1].set_title("Top 20 shared stops by number of routes")
fig.tight_layout(); PL.save_fig(fig, "fig14_top_routes_shared_stops.png")

# %% [markdown]
# ## 5 · Route connectivity and stop accessibility to metro

# %%
conn = N.connectivity(spark, clean, D.metro_stations())
pd.Series(conn["summary"]).round(3)

# %%
PL.save_table(pd.DataFrame([conn["summary"]]), "network_connectivity_summary.csv")
PL.save_table(conn["route_degree"], "network_route_connectivity.csv")
deg = conn["stop_degree"].routes
print("routes per stop:", deg.describe().round(1).to_dict())
conn["route_degree"].head(10)

# %%
fig, ax = plt.subplots(1, 2, figsize=(13, 3.8))
ax[0].hist(deg.clip(upper=60), bins=60, color="#1f6fb2"); ax[0].set_yscale("log")
ax[0].set_title("Routes serving each stop (log scale)"); ax[0].set_xlabel("routes (last bar = 60 or more)")
d = conn["stop_to_metro"].metro_m / 1000
ax[1].hist(d.clip(upper=15), bins=60, color="#1f6fb2"); ax[1].axvline(0.4, color="k", ls="--"); ax[1].axvline(0.8, color="k", ls=":")
ax[1].set_title("Distance from each bus stop to nearest metro station"); ax[1].set_xlabel("km (dashed 400 m, dotted 800 m; last bar = 15 km or more)")
fig.tight_layout(); PL.save_fig(fig, "fig15_connectivity.png")

# %% [markdown]
# ## 6 · Metro ridership demand patterns (Spark SQL)

# %%
dem = N.metro_demand(spark)
for k in ("hourly", "busiest", "peak", "by_line", "top_od"):
    PL.save_table(dem[k], f"metro_demand_{k}.csv")
dem["peak"]

# %%
dem["busiest"].head(10)

# %%
dem["top_od"].head(10)

# %%
fig, ax = plt.subplots(1, 3, figsize=(18, 4.5), gridspec_kw={"width_ratios": [1, 1, 1.3]})
h = dem["hourly"]
for (p, dt), g in h.groupby(["period", "daytype"]):
    ax[0].plot(g.hour, g.avg_entries, marker=".", ls="-" if dt == "weekday" else "--", label=f"{p}, {dt}")
ax[0].set_title("Average entries per hour, all stations"); ax[0].set_xlabel("hour"); ax[0].legend(fontsize=7)
b = dem["busiest"].head(15).iloc[::-1]
short = b.station.str.replace("Nadaprabhu Kempegowda Station, ", "", regex=False).str.slice(0, 26)
ax[1].barh(short, b.avg_daily_entries, color="#1f6fb2"); ax[1].set_title("Busiest stations, weekday entries (1-10 Aug)")
bl = dem["by_line"].pivot_table(index="date", columns="line", values="entries", aggfunc="sum")
bl.index = pd.to_datetime(bl.index)
bl = bl.reindex(pd.date_range(bl.index.min(), bl.index.max()))   # NaN for 19-31 Aug: no line drawn across the gap
bl.plot(ax=ax[2], marker=".", lw=1); ax[2].set_title("Daily entries by line (no data 19-31 Aug)"); ax[2].set_xlabel("")
ax[2].legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.0, 1.0))
fig.tight_layout(); PL.save_fig(fig, "fig16_metro_demand.png")

# %% [markdown]
# ## 7 · Network size over time (all GTFS snapshots in HDFS)

# %%
over = N.network_over_time(spark, snaps)
PL.save_table(over, "network_over_time.csv")
ax = over.set_index(pd.to_datetime(over.snapshot))[["stops", "routes", "weekday_trips"]].plot(subplots=True, marker="o", figsize=(10, 6), legend=True)
ax[0].figure.suptitle("BMTC network size per GTFS snapshot")
PL.save_fig(ax[0].figure, "fig17_network_over_time.png")
over

# %% [markdown]
# ## 8 · Storage format: CSV vs Parquet on HDFS

# %%
bench = N.storage_benchmark(spark, SNAP)
PL.save_table(bench, "storage_csv_vs_parquet.csv")
bench.pivot(index="task", columns="format", values="seconds_median").round(2)

# %% [markdown]
# **Reading the results.** Parquet is columnar and compressed: it is smaller on disk and faster for queries that touch
# few columns, which is why the pipeline stores data as Parquet on HDFS while keeping the original CSV/GTFS text files
# as the raw layer.

# %%
spark.stop()
