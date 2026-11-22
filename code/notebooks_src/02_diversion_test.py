# %% [markdown]
# # 02 · Main result: origin-destination diversion test
# **Question.** From the *same origin*, did the share of metro trips going to stations with strong bus
# links to the Yellow corridor fall after 11 Aug 2025?
#
# $$\log(1+\text{trips}_{o,d,t,b}) = \alpha_{o,t,b} + \gamma_{o,d,b} + \beta\,\text{post}_t\times z\text{YellowLink}_d + \varepsilon$$
#
# * $\alpha_{o,t,b}$ (origin × date × band) absorbs everything happening at an origin on a given day
#   and time band: flower show crowds, joyriders, rain, holidays.
# * $\gamma_{o,d,b}$ (origin × destination × band) absorbs the normal size of every flow.
# * $\beta<0$ means bus-linked destinations lost share. SEs clustered by destination (67 clusters).
#
# Attach `t15-data`, `t15-code` and the **output of notebook 01** (for the frozen list).
# Run this only after the pre-registration has been uploaded.

# %%
SETUP

# %%
from t15 import env, panels as P, econ as E
import pandas as pd, numpy as np, matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats

# %%
spark = env.start(cores=4, memory="20g")
if not D.hdfs_has(spark, "metro/od"):
    D.ingest_to_hdfs(spark, snapshots=[C.SNAPSHOT_BEFORE])

# %% [markdown]
# ## Build the panel with Spark SQL (from HDFS)

# %%
spark.read.parquet(env.hdfs_path("metro/od")).createOrReplaceTempView("od")
spark.read.parquet(env.hdfs_path("metro/stations")).createOrReplaceTempView("stations")
band_sql = spark.sql("""
  SELECT o.origin, o.dest, o.date,
         CASE WHEN hour BETWEEN 7 AND 10 THEN 'am_peak' WHEN hour BETWEEN 11 AND 15 THEN 'midday'
              WHEN hour BETWEEN 16 AND 20 THEN 'pm_peak' ELSE 'other' END AS band,
         SUM(trips) AS trips
  FROM od o
  JOIN stations so ON so.station = o.origin AND NOT so.is_yellow_new
  JOIN stations sd ON sd.station = o.dest   AND NOT sd.is_yellow_new
  WHERE o.origin <> o.dest AND o.dest <> 'Rashtreeya Vidyalaya Road'
  GROUP BY o.origin, o.dest, o.date, band""")
print("non-zero cells from Spark SQL:", band_sql.count())
od_pd = spark.read.parquet(env.hdfs_path("metro/od")).toPandas()
panel = P.od_panel(od_pd, by="band")
print("balanced panel:", panel.shape, "| zero cells:", (panel.trips == 0).mean().round(3))
assert abs(panel.trips.sum() - band_sql.agg({"trips": "sum"}).first()[0]) < 1   # Spark and pandas agree

# %%
scores = PL.get_scores()
transfer = PL.get_transfer_list()
panel = P.attach_exposure(panel, scores, "dest", transfer=transfer)
FE = ["fe_o_t", "fe_o_d"]

# %% [markdown]
# ## Main estimates

# %%
res = []
m1 = E.fit(panel, "ltrips", ["post_zYellowLink_d"], FE, "dest");               res.append(E.tidy(m1, "OLS · YellowLink (primary)"))
m2 = E.fit(panel, "ltrips", ["post_transfer_d"], FE, "dest");                  res.append(E.tidy(m2, "OLS · frozen transfer stations"))
m3 = E.fit(panel, "trips", ["post_zYellowLink_d"], FE, "dest", model="ppml");   res.append(E.tidy(m3, "PPML · YellowLink"))
m4 = E.fit(panel, "trips", ["post_transfer_d"], FE, "dest", model="ppml");      res.append(E.tidy(m4, "PPML · transfer stations"))
m5 = E.fit(panel, "ltrips", ["post_zYellowLink_d"], FE, ["origin", "dest"]);    res.append(E.tidy(m5, "OLS · two-way clustered"))
m6 = E.fit(panel, "ltrips", ["post_zYellowLinkDir_d"], FE, "dest");            res.append(E.tidy(m6, "OLS · YellowLinkDir"))
m7 = E.fit(panel, "ltrips", ["post_zCollinear_d"], FE, "dest");                res.append(E.tidy(m7, "OLS · Collinear"))
main = pd.concat(res, ignore_index=True)
main["pct_effect"] = (np.exp(main["Estimate"]) - 1) * 100
PL.save_table(main, "main_diversion_estimates.csv")
main[["model", "term", "Estimate", "Std. Error", "Pr(>|t|)", "2.5%", "97.5%", "pct_effect", "nobs"]].round(4)

# %% [markdown]
# **Reading it:** for `post_zYellowLink_d`, the estimate is the % change (≈ 100 × β) in trips to a
# destination whose YellowLink is one standard deviation above average, relative to other destinations
# from the same origin, after the opening. For `post_transfer_d` it is the change for the 10 frozen stations.

# %% [markdown]
# ## Inference with few clusters: wild-cluster bootstrap and randomisation inference

# %%
wb = E.wild_cluster_bootstrap(panel, "ltrips", "post_zYellowLink_d", FE, "dest", reps=9999)
z_station = scores.set_index("station").loc[panel.dest.unique(), "YellowLink"]
ri = E.randomization_inference(panel, "ltrips", "dest", z_station, FE, n_perm=1000)
inf = pd.DataFrame([{"test": "wild cluster bootstrap (Webb, 9,999)", "beta": wb["beta"], "p": wb["p_value"]},
                    {"test": "randomisation inference (1,000 permutations)", "beta": ri["beta"], "p": ri["p_value"]}])
PL.save_table(inf, "main_inference.csv")
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.hist(ri["dist"], bins=40, color="#9aa6b5"); ax.axvline(ri["beta"], c="crimson", lw=2, label=f"actual β = {ri['beta']:.4f}")
ax.set_xlabel("β with YellowLink shuffled across destinations"); ax.legend(); ax.set_title(f"Randomisation inference, p = {ri['p_value']:.3f}")
PL.save_fig(fig, "fig_ri_distribution.png")
inf

# %% [markdown]
# ## Figure 2 · Event study by day (reference: Thu 7 Aug)

# %%
es = E.event_study(panel, "ltrips", "zYellowLink_d", FE, "dest", ref=C.REFERENCE_DAY)
es_t = E.event_study(panel, "ltrips", "transfer_d", FE, "dest", ref=C.REFERENCE_DAY)
PL.save_table(es, "event_study_yellowlink.csv"); PL.save_table(es_t, "event_study_transfer.csv")
fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharex=True)
for ax, e, title in ((axes[0], es, "post × zYellowLink (per SD)"), (axes[1], es_t, "frozen bus-transfer stations")):
    x = pd.to_datetime(e["date"])
    ax.errorbar(x, e["Estimate"], yerr=1.96 * e["Std. Error"], fmt="o", capsize=3, c="#1f6fb2")
    ax.axhline(0, c="k", lw=0.8); ax.axvline(pd.Timestamp(C.OPENING_DATE) - pd.Timedelta(hours=12), c="#d9a400", lw=2, ls="--")
    for dday in C.EVENT_DAYS: ax.axvspan(pd.Timestamp(dday) - pd.Timedelta(hours=12), pd.Timestamp(dday) + pd.Timedelta(hours=12), color="#eee")
    ax.set_title(title); ax.tick_params(axis="x", rotation=45)
axes[0].set_ylabel("effect on log(1+trips) vs 7 Aug")
fig.suptitle("Trips to bus-linked destinations, same origin, by day (dashed = Yellow Line opens)")
PL.save_fig(fig, "fig2_event_study.png")

# %% [markdown]
# ## Figure 3 · Do the same origins lose bus-transfer trips and gain Yellow trips?

# %%
osh = P.origin_shift_table(transfer)
osh = osh[osh.origin != C.INTERCHANGE]
from scipy import stats
rho, p_rho = stats.spearmanr(osh.d_share_transfer, osh.d_share_yellow, nan_policy="omit")
w = osh.trips_per_day_pre
import statsmodels.api as sm
wls = sm.WLS(osh.d_share_yellow, sm.add_constant(osh.d_share_transfer), weights=w, missing="drop").fit(cov_type="HC1")
PL.save_table(osh, "origin_shifts.csv")
print(f"Spearman rho = {rho:.3f} (p = {p_rho:.3g}); WLS slope = {wls.params.iloc[1]:.3f} (SE {wls.bse.iloc[1]:.3f})")
fig, ax = plt.subplots(figsize=(6.5, 5))
ax.scatter(osh.d_share_transfer * 100, osh.d_share_yellow * 100, s=w / w.max() * 300, alpha=0.6, c="#7d3c98")
for _, r in osh.nlargest(6, "d_share_yellow").iterrows():
    ax.annotate(r.origin.split(",")[0], (r.d_share_transfer * 100, r.d_share_yellow * 100), fontsize=7)
ax.axvline(0, c="k", lw=0.6); ax.set_xlabel("change in share of trips to bus-transfer stations (pp)")
ax.set_ylabel("share of trips to new Yellow stations after opening (pp)")
ax.set_title(f"Each dot is an origin (size = trips). Spearman ρ = {rho:.2f}")
PL.save_fig(fig, "fig3_origin_matching.png")

# %% [markdown]
# ## Comparison · naive before/after vs the fixed-effects design
# The naive approach (as in the earlier blog analysis) compares each station's daily exits before and
# after, with no control for what happened at the origins or on each day.

# %%
exi = D.load_station_hourly("exits")
olds = [s for s in P.old_stations() if s != C.INTERCHANGE]
wd = exi[exi.station.isin(olds) & (pd.to_datetime(exi.date).dt.dayofweek < 5) & ~exi.date.isin(list(C.EVENT_DAYS))]
daily = wd.groupby(["station", "date"]).exits.sum().reset_index()
daily["post"] = daily.date.isin(C.POST_DAYS)
naive = daily.groupby(["station", "post"]).exits.mean().unstack()
naive["pct_chg"] = (naive[True] / naive[False] - 1) * 100
naive = naive.join(scores.set_index("station")[["YellowLink"]])
nfit = sm.OLS(naive["pct_chg"], sm.add_constant((naive.YellowLink - naive.YellowLink.mean()) / naive.YellowLink.std())).fit(cov_type="HC1")
cmp_tab = pd.DataFrame([
    {"design": "naive station before/after (exits, % per SD YellowLink)", "estimate": nfit.params.iloc[1], "se": nfit.bse.iloc[1], "n": len(naive)},
    {"design": "fixed-effects diversion test (% per SD YellowLink)", "estimate": 100 * m1.coef().iloc[0], "se": 100 * m1.se().iloc[0], "n": m1._N},
])
PL.save_table(cmp_tab, "naive_vs_fe.csv")
PL.save_table(naive.reset_index(), "naive_station_changes.csv")
cmp_tab

# %%
spark.stop()
