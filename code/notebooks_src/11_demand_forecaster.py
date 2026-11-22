# %% [markdown]
# # 11 · Next-day metro demand forecaster (Spark MLlib)
# A model built from our data for a real use: for every station and hour of tomorrow, forecast BMRCL entries,
# give a calibrated 90% range and a crowding warning, and flag unusual hours.
# * Learn 8-17 Sep 2025, calibrate ranges 18-21 Sep, test once on 22-30 Sep (never seen; includes Navaratri).
# * Scored against "same hour yesterday" and "same hour last week".
# * V1 learns the level; V2 learns the change from last week (tested, worse); V3 adds hourly weather
#   (Open-Meteo rain and temperature, used as observed). Final: V1 Random Forest.
# * What each input group is worth, with 95% ranges from 1,000 bootstrap resamples of test days.
# * Stations grouped by weekday rhythm with MLlib KMeans (silhouette).

# %%
SETUP

# %%
from t15 import forecast as F, lines as L, env
import pandas as pd, numpy as np, matplotlib.pyplot as plt
pop = PL.get_population(800)
_, bus_tot = L.bus_station_hourly(C.SNAPSHOT_BEFORE, None)
tab = F.build_table(bus_tot, pop)
tab.split.value_counts()

# %%
spark = env.start(cores=4, memory="20g", hdfs=False)
ev = F.evaluate(spark, tab)
PL.save_table(ev["results"], "forecast_results.csv"); PL.save_table(ev["ablation"], "forecast_ablation.csv")
ev["results"].round(2)

# %%
ev["ablation"].round(2)

# %%
iw = F.intervals_and_warnings(ev["preds"]["V1 Random Forest, level"], tab)
for k in ("coverage", "warnings", "q", "anomalies"):
    PL.save_table(iw[k], f"forecast_{k}.csv")
PL.save_table(iw["test_preds"], "forecast_test_predictions.csv")
pd.concat([iw["coverage"].round(3), iw["warnings"].round(3)], axis=1)

# %%
cl, sil = F.cluster_stations(spark)
PL.save_table(cl, "station_clusters.csv"); PL.save_table(sil, "cluster_silhouette.csv")
sil.round(3)

# %%
tp = iw["test_preds"]
fig, ax = plt.subplots(1, 2, figsize=(15, 4))
s = tp[tp.station == "Nadaprabhu Kempegowda Station, Majestic"].sort_values(["day", "hour"])
x = np.arange(len(s))
ax[0].fill_between(x, s.lo, s.hi, alpha=.25, label="90% range"); ax[0].plot(x, s.pred, label="forecast"); ax[0].plot(x, s.entries, ".", ms=3, label="actual")
ax[0].set_title("Majestic, 22-30 Sep: forecast vs actual (station-hours)"); ax[0].legend()
r = ev["results"].sort_values("skill_vs_best_simple_pct")
ax[1].barh(r.method, r.skill_vs_best_simple_pct, xerr=[r.skill_vs_best_simple_pct - r.skill_ci_low, r.skill_ci_high - r.skill_vs_best_simple_pct], color="#1f6fb2")
ax[1].axvline(0, color="k"); ax[1].set_title("Smaller average miss than 'same hour last week' (%)")
PL.save_fig(fig, "fig19_forecaster.png")

# %%
spark.stop()
