# %% [markdown]
# # 04 · How did BMTC respond? Bus supply across 26 GTFS snapshots (Jan 2024 → Nov 2026)
# * **Supply event study:** weekday bus trips within 400 m walk of each metro station, per snapshot.
#   New Yellow stations vs old stations, relative to the 4 Aug 2025 snapshot.
# * **Old links:** trips on routes joining the frozen bus-transfer stations to the Yellow corridor over time.
#   Did BMTC cut the bus legs that the metro made redundant?
# * **Route diff 4 Aug → 2 Sep 2025:** routes added or removed around Yellow stations (MF feeder routes).
#
# The same aggregation also runs as a **Spark job on HDFS** over all snapshots; that version is the one timed in notebook 06.

# %%
SETUP

# %%
from t15 import bus as B, econ as E, env
import pandas as pd, numpy as np, matplotlib.pyplot as plt
stations = D.metro_stations()
transfer = PL.get_transfer_list()

# %% [markdown]
# ## Spark job on HDFS (all snapshots, straight-line 400 m)

# %%
spark = env.start(cores=4, memory="20g")
missing = [s for s in C.BMTC_SNAPSHOTS if not D.hdfs_has(spark, f"gtfs/stop_times/snapshot={s}")]
if missing:
    D.ingest_to_hdfs(spark, snapshots=missing)
sup_spark = B.spark_supply(spark, stations).toPandas()
PL.save_table(sup_spark, "supply_spark_straight400.csv")
sup_spark.groupby("snapshot").trips.sum().plot(marker="o", figsize=(8, 3), title="Bus trips within 400 m of any metro station (Spark)")

# %% [markdown]
# ## Walking-distance version (pandas, OSM network)

# %%
f = PL.find_output("tables/supply_walk400.csv")
if f is not None:
    sup = pd.read_csv(f)
else:
    sup = B.supply_panel(router=PL.router())
    PL.save_table(sup, "supply_walk400.csv")
sup["group"] = np.select([sup.station.isin(C.YELLOW_NEW), sup.station.isin(transfer)],
                         ["new Yellow stations", "frozen bus-transfer stations"], "other old stations")
sup["ltrips"] = np.log1p(sup.trips)
sup["ltrips_net"] = sup["ltrips"] - np.log(sup.total_trips_network)   # share of network supply
g = sup.groupby(["snapshot", "group"]).trips.sum().unstack()
g.tail()

# %%
# supply event study: station FE + snapshot FE, Yellow x snapshot (ref = 2025-08-04)
sup["yellow"] = sup.station.isin(C.YELLOW_NEW).astype(float)
sup["transfer"] = sup.station.isin(transfer).astype(float)
sup["fe_s"] = pd.factorize(sup.station)[0]; sup["fe_t"] = pd.factorize(sup.snapshot)[0]
es_y = E.event_study(sup, "ltrips", "yellow", ["fe_s", "fe_t"], "station", time_col="snapshot", ref=C.SNAPSHOT_BEFORE)
es_tr = E.event_study(sup[~sup.station.isin(C.YELLOW_NEW)], "ltrips", "transfer", ["fe_s", "fe_t"], "station",
                      time_col="snapshot", ref=C.SNAPSHOT_BEFORE)
PL.save_table(es_y, "supply_event_study_yellow.csv"); PL.save_table(es_tr, "supply_event_study_transfer.csv")
fig, ax = plt.subplots(figsize=(11, 4))
for e, c, lab, off in ((es_y, "#d9a400", "new Yellow stations vs old", -6), (es_tr, "crimson", "bus-transfer vs other old", 6)):
    x = pd.to_datetime(e.snapshot) + pd.Timedelta(days=off)
    ax.errorbar(x, e.Estimate, yerr=1.96 * e["Std. Error"], fmt="o-", capsize=2, c=c, label=lab, ms=4)
ax.axhline(0, c="k", lw=0.6); ax.axvline(pd.Timestamp(C.OPENING_DATE), ls="--", c="#d9a400")
ax.set_ylabel("log bus trips within 400 m, vs 4 Aug 2025"); ax.legend(); ax.set_title("Bus supply around metro stations, 26 GTFS snapshots")
PL.save_fig(fig, "fig6_supply_event_study.png")

# %% [markdown]
# ## Old bus links: trips joining the bus-transfer stations to the Yellow corridor, per snapshot

# %%
rows = []
for snap in C.BMTC_SNAPSHOTS:
    if not D.gtfs_path(snap).exists(): continue
    sc = B.station_scores(snap, router=PL.router(), stations=stations)
    rows.append(sc[["station", "BusTrips", "YellowLinkTrips", "YellowLink"]].assign(snapshot=snap))
links = pd.concat(rows); PL.save_table(links, "yellowlink_by_snapshot.csv")
lt = links[links.station.isin(transfer)].groupby("snapshot")[["YellowLinkTrips", "BusTrips"]].sum()
ax = lt.plot(marker="o", figsize=(9, 3.5), title="Frozen bus-transfer stations: linking trips and all trips")
ax.axvline(list(lt.index).index(C.SNAPSHOT_AFTER) - 0.5 if C.SNAPSHOT_AFTER in lt.index else 0, ls="--", c="#d9a400")
PL.save_fig(ax.get_figure(), "fig7_old_links.png")

# %% [markdown]
# ## Route diff around Yellow stations: 4 Aug → 2 Sep 2025

# %%
rd = B.route_diff()
PL.save_table(rd, "route_diff_yellow.csv")
print(rd.status.value_counts())
rd[rd.status != "kept"].head(30)

# %%
spark.stop()
