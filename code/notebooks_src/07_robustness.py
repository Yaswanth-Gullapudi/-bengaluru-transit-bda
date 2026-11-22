# %% [markdown]
# # 07 · Robustness: every pre-registered check
# Each row re-estimates the primary model (`log(1+trips) ~ post × zYellowLink_d | o×date×band + o×d×band`,
# SE clustered by destination) under one change.
#
# | Check | Why |
# |---|---|
# | Geography controls (`post × hops to RV Road`, `post × line`, `post × BusTrips`) | Is YellowLink just "close to the new line"? |
# | Within Green only / Purple only | Compare destinations on the same line |
# | Placebo openings 5 Aug, 7 Aug (pre-period only) | A fake date should show nothing |
# | Drop 15–16 Aug; drop Lalbagh & Mahalakshmi; drop 11–12 Aug | Holidays, flower show, joyriders |
# | 800 m catchment; 400 m corridor; 2 Sep snapshot | Measurement choices |
# | Hourly panel instead of time bands | Aggregation choice |
# | Wild-cluster bootstrap, randomisation inference | Few clusters (67) |

# %%
SETUP

# %%
from t15 import panels as P, econ as E
import pandas as pd, numpy as np, matplotlib.pyplot as plt
od = D.load_od()
scores = PL.get_scores()
transfer = PL.get_transfer_list()
FE = ["fe_o_t", "fe_o_d"]
base = P.attach_exposure(P.od_panel(od), scores, "dest", transfer=transfer)
rows = []
def run(label, df, x="post_zYellowLink_d", extra=(), y="ltrips", model="ols", cluster="dest"):
    m = E.fit(df, y, [x, *extra], FE, cluster, model)
    t = E.tidy(m, label, keep=[x]); rows.append(t); return t

run("primary", base)

# %% [markdown]
# ## Geography and correlated exposures

# %%
old = scores[~scores.is_yellow_new & (scores.station != C.INTERCHANGE)]
print("Spearman correlation YellowLink vs hops to RV Road:",
      round(old[["YellowLink", "MetroHopsToRV"]].corr(method="spearman").iloc[0, 1], 3))
base["post_purple_d"] = base.post * base.line_d.str.contains("PURPLE").astype(int)
run("+ post × hops to RV Road", base, extra=["post_zMetroHopsToRV_d"])
run("+ post × line", base, extra=["post_purple_d"])
run("+ post × BusTrips", base, extra=["post_zBusTrips_d"])
run("+ all three controls", base, extra=["post_zMetroHopsToRV_d", "post_purple_d", "post_zBusTrips_d"])
run("destinations on Green only", base[base.line_d.str.contains("GREEN")])
run("destinations on Purple only", base[base.line_d.str.contains("PURPLE")])
run("excluding near-corridor destinations", base[~base.dest.map(scores.set_index("station").near_corridor).astype(bool)])

# %% [markdown]
# ## Placebo opening dates (pre-period only)

# %%
for pdate in C.PLACEBO_DATES:
    pre = P.od_panel(od, days=C.PRE_DAYS)
    pre["post"] = (pre.date >= pdate).astype(int)
    pre = P.attach_exposure(pre, scores, "dest", transfer=transfer)
    run(f"placebo opening {pdate}", pre)

# %% [markdown]
# ## Event days, stations, joyriders

# %%
run("drop 15–16 Aug", base[~base.date.isin(["2025-08-15", "2025-08-16"])])
run("drop 8 Aug festival", base[base.date != "2025-08-08"])
drop_st = C.FLOWER_SHOW_STATIONS + C.FESTIVAL_STATIONS
run("drop Lalbagh & Mahalakshmi (as origin or destination)", base[~base.origin.isin(drop_st) & ~base.dest.isin(drop_st)])
run("drop 11–12 Aug (joyriders)", base[~base.date.isin(C.JOYRIDE_DAYS)])
run("weekdays only", base[pd.to_datetime(base.date).dt.dayofweek < 5])

# %% [markdown]
# ## Measurement choices

# %%
for (snap, cm, ym), lab in (((C.SNAPSHOT_BEFORE, 800, 800), "800 m catchment"),
                            ((C.SNAPSHOT_BEFORE, 400, 400), "400 m corridor"),
                            ((C.SNAPSHOT_AFTER, 400, 800), "exposure from 2 Sep snapshot")):
    alt = P.attach_exposure(P.od_panel(od), PL.get_scores(snap, cm, ym), "dest", transfer=transfer)
    run(lab, alt)
hourly = P.attach_exposure(P.od_panel(od, by="hour"), scores, "dest", transfer=transfer)
hourly = hourly[(hourly.hour >= 6) & (hourly.hour <= 22)]
run("hourly panel (6–22 h)", hourly)
run("PPML", base, y="trips", model="ppml")
run("two-way clustering", base, cluster=["origin", "dest"])
run("YellowLinkDir", base, x="post_zYellowLinkDir_d")

# %% [markdown]
# ## Inference with few clusters

# %%
wb = E.wild_cluster_bootstrap(base, "ltrips", "post_zYellowLink_d", FE, "dest", reps=9999)
ri = E.randomization_inference(base, "ltrips", "dest", scores.set_index("station").loc[base.dest.unique(), "YellowLink"], FE, n_perm=1000)
print("wild bootstrap p =", round(wb["p_value"], 4), "| randomisation p =", round(ri["p_value"], 4))

# %% [markdown]
# ## Table and Figure 10 · coefficient plot

# %%
rob = pd.concat(rows, ignore_index=True)
PL.save_table(rob, "robustness.csv")
fig, ax = plt.subplots(figsize=(7, 0.32 * len(rob) + 1))
y = np.arange(len(rob))[::-1]
ax.errorbar(rob.Estimate, y, xerr=1.96 * rob["Std. Error"], fmt="o", c="#1f6fb2", capsize=2)
ax.axvline(0, c="k", lw=0.6); ax.axvline(rob.Estimate.iloc[0], c="#d9a400", ls="--", lw=1)
ax.set_yticks(y); ax.set_yticklabels(rob.model, fontsize=8)
ax.set_xlabel("β on post × zYellowLink (95% CI)"); ax.set_title("Robustness of the diversion estimate")
PL.save_fig(fig, "fig10_robustness.png")
rob[["model", "Estimate", "Std. Error", "Pr(>|t|)", "nobs"]].round(4)
