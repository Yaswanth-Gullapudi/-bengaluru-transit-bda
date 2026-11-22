# %% [markdown]
# # 06 · Spark scaling and Spark vs pandas
# **Job** (identical logic in both engines): for N BMTC GTFS snapshots, find bus stops within 400 m of
# each metro station, join with `stop_times` and `trips`, and count weekday trips and routes per station
# per snapshot; plus the origin-destination time-band aggregation of the metro table.
#
# * **Data size:** N = 1, 5, 10, 20, 26 real snapshots (≈1.4 M → ≈38 M `stop_times` rows)
# * **Strong scaling:** Spark `local[1]`, `local[2]`, `local[4]` (Kaggle CPU notebooks have 4 cores)
# * **Baseline:** the same job in pandas on one core
# * 3 repeats each, median reported. Input read from HDFS.
#
# Run this in its own session on the second Kaggle account if the first is busy.

# %%
SETUP

# %%
from t15 import env, scaling
import pandas as pd, matplotlib.pyplot as plt
spark = env.start(cores=4, memory="20g")
missing = [s for s in C.BMTC_SNAPSHOTS if not D.hdfs_has(spark, f"gtfs/stop_times/snapshot={s}")]
if missing:
    D.ingest_to_hdfs(spark, snapshots=missing)
if not D.hdfs_has(spark, "metro/od"):
    D.ingest_to_hdfs(spark, snapshots=[])
spark.stop()

# %%
res = scaling.run(sizes=(1, 5, 10, 20, 26), cores=(1, 2, 4), repeats=3, pandas_max=26, memory="20g")
PL.save_table(res.drop(columns=["seconds_all"]), "scaling_results.csv")
res.drop(columns=["seconds_all"])

# %% [markdown]
# ## Figure 9 · Runtime vs data size, and speed-up vs cores

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
sp = res[res.engine == "spark"]
for c, col in zip((1, 2, 4), ("#9aa6b5", "#7d3c98", "#1f6fb2")):
    s = sp[sp.cores == c]
    axes[0].plot(s.snapshots, s.seconds_median, "-o", c=col, label=f"Spark local[{c}]")
pdx = res[res.engine == "pandas"]
axes[0].plot(pdx.snapshots, pdx.seconds_median, "-s", c="crimson", label="pandas (1 core)")
axes[0].set_xlabel("GTFS snapshots processed"); axes[0].set_ylabel("seconds (median of 3)"); axes[0].legend()
axes[0].set_title("Runtime vs data size")
for n in sorted(sp.snapshots.unique()):
    s = sp[sp.snapshots == n].sort_values("cores")
    axes[1].plot(s.cores, s.speedup_vs_1core, "-o", label=f"{n} snapshots")
axes[1].plot([1, 4], [1, 4], "k--", lw=0.8, label="ideal")
axes[1].set_xlabel("cores"); axes[1].set_ylabel("speed-up vs 1 core"); axes[1].legend(fontsize=8)
axes[1].set_title("Strong scaling")
PL.save_fig(fig, "fig9_scaling.png")
