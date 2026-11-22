# %% [markdown]
# # 05 · Spark MLlib: does bus-network data improve prediction?
# **Task.** Predict hourly entries at the 68 old metro stations after the Yellow Line opened.
# * Train: 11–18 Aug 2025 (8 days, 3-fold cross-validation for hyper-parameters)
# * Test: 1–30 Sep 2025 (out of time; hour 6 dropped because the first train moved)
#
# **Targets**
# * `y_level` = log(1 + entries)
# * `y_change` = log(1 + entries) − log(1 + same station-hour average before the opening): the *redistribution*
#
# **Models:** Linear Regression (elastic net), Random Forest, Gradient-Boosted Trees.
#
# **Feature sets**
# | Set | Features |
# |---|---|
# | metro only | hour, day of week, weekend, holiday, pre-opening level (same hour, daily), hops to RV Road, line, location, population within 800 m |
# | metro + bus | + BusTrips, BusRoutes, BusStops, YellowLink, YellowLinkDir, YellowLinkTrips, Collinear |
# | metro + shuffled bus (placebo) | + the same bus features shuffled across stations |
#
# The placebo matters: with 68 stations, *any* station-level number partly acts as a station ID.
# Bus data adds real information only if **metro + bus** beats **metro + shuffled bus**.

# %%
SETUP

# %%
from t15 import env, ml
import pandas as pd, numpy as np, matplotlib.pyplot as plt
spark = env.start(cores=4, memory="24g", hdfs=False)   # in-memory ML; HDFS not needed here
table = ml.feature_table(PL.get_scores(), PL.get_population(800))
print(table.shape, table.split.value_counts().to_dict())
table.head()

# %%
import time
t0 = time.time()
metrics, imps = ml.run_comparison(spark, table, targets=("y_level", "y_change"), folds=3)
print(f"total {time.time()-t0:.0f}s")
PL.save_table(metrics, "mllib_metrics.csv"); PL.save_table(imps, "mllib_importances.csv")

# %% [markdown]
# ## Comparison table (September test set)

# %%
test = metrics[metrics.split == "test_sep"]
tab = test.pivot_table(index=["target", "model"], columns="features", values=["rmse", "mae", "r2"]).round(4)
tab

# %%
# improvement of real bus features over metro-only and over the placebo
piv = test.pivot_table(index=["target", "model"], columns="features", values="rmse")
gain = pd.DataFrame({
    "rmse_metro_only": piv["metro_only"],
    "rmse_plus_bus": piv["metro_plus_bus"],
    "rmse_plus_placebo": piv["metro_plus_placebo"],
})
gain["gain_vs_metro_%"] = (1 - gain.rmse_plus_bus / gain.rmse_metro_only) * 100
gain["gain_vs_placebo_%"] = (1 - gain.rmse_plus_bus / gain.rmse_plus_placebo) * 100
PL.save_table(gain.reset_index(), "mllib_gain.csv")
gain.round(4)

# %% [markdown]
# ## Figure 8 · RMSE by model and feature set; feature importance

# %%
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for ax, tgt in zip(axes[:2], ("y_level", "y_change")):
    p = piv.loc[tgt][["metro_only", "metro_plus_placebo", "metro_plus_bus"]]
    p.plot.bar(ax=ax, color=["#9aa6b5", "#d0c4dc", "#1f6fb2"], rot=0)
    ax.set_title(f"{tgt}: test RMSE (September)"); ax.set_ylabel("RMSE"); ax.set_ylim(p.values.min() * 0.95, p.values.max() * 1.02)
imp = imps[(imps.model == "GBT") & (imps.features == "metro_plus_bus") & (imps.target == "y_change")]
imp = imp[~imp.feature.str.match(r"(hour|dow)_\d+")].nlargest(12, "importance")
axes[2].barh(imp.feature[::-1], imp.importance[::-1], color=["#d9a400" if f in ml.BUS_FEATURES else "#9aa6b5" for f in imp.feature[::-1]])
axes[2].set_title("GBT importance, y_change (yellow = bus features)")
PL.save_fig(fig, "fig8_mllib_comparison.png")

# %%
spark.stop()
