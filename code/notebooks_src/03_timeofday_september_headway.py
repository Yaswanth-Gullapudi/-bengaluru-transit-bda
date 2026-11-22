# %% [markdown]
# # 03 · Time-of-day signature, persistence into September, and the headway cut
# Three checks on the mechanism, using station-level hourly entries and exits:
#
# 1. **Time-of-day signature (H3).** Commuters who used to leave the metro at a bus-transfer station
#    in the morning (and board there in the evening) should disappear: AM-peak **exits** and PM-peak
#    **entries** fall; midday does not. Flower-show or festival crowds would do the opposite.
# 2. **Persistence.** Does the drop last through September (30 days, 3–7 weeks after opening)?
# 3. **Headway elasticity.** On 10 Sep 2025 a 4th train cut the Yellow headway from 25 to 19 minutes.
#    How much did Yellow-station entries respond, and more so where BMTC added feeder buses?

# %%
SETUP

# %%
from t15 import panels as P, econ as E, bus as B
import pandas as pd, numpy as np, matplotlib.pyplot as plt
scores = PL.get_scores()
transfer = PL.get_transfer_list()
olds = [s for s in P.old_stations() if s != C.INTERCHANGE]

# %% [markdown]
# ## 1 · Time-of-day signature (1–18 Aug)

# %%
sp = P.station_panel(C.AUG_DAYS, stations=olds)
sp["post"] = sp.date.isin(C.POST_DAYS).astype(int)
sp = P.attach_exposure(sp, scores, "station", transfer=transfer)
bands = ["am_peak", "midday", "pm_peak", "other"]
for b in bands:
    sp[f"pt_{b}"] = sp.post * sp.transfer_s * (sp.band == b)
    sp[f"pz_{b}"] = sp.post * sp.zYellowLink_s * (sp.band == b)
rows = []
for kind in ("lentries", "lexits"):
    for pref, lab in (("pt", "transfer stations"), ("pz", "per SD YellowLink")):
        m = E.fit(sp, kind, [f"{pref}_{b}" for b in bands], ["fe_s_h", "fe_t_h"], "station")
        t = E.tidy(m, f"{kind} · {lab}"); rows.append(t)
tod = pd.concat(rows, ignore_index=True)
tod["band"] = tod.term.str.split("_", n=1).str[1]
PL.save_table(tod, "timeofday_estimates.csv")
tod.pivot_table(index="model", columns="band", values="Estimate").round(4)[bands]

# %%
# Figure 4 · hourly post/pre ratio on weekdays, transfer stations vs the rest
wd = sp[(sp.dow < 5) & ~sp.date.isin(list(C.EVENT_DAYS))]
prof = wd.groupby(["transfer_s", "post", "hour"])[["entries", "exits"]].mean().unstack("post")
fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
for ax, kind in zip(axes, ("exits", "entries")):
    for tr, c, lab in ((1, "crimson", "frozen bus-transfer stations"), (0, "#888", "other old stations")):
        r = prof.loc[tr][kind][1] / prof.loc[tr][kind][0]
        r = r[(r.index >= 6) & (r.index <= 22)]
        ax.plot(r.index, (r - 1) * 100, "-o", c=c, ms=3, label=lab)
    ax.axhline(0, c="k", lw=0.6); ax.axvspan(7, 10.9, color="#fff3c4"); ax.axvspan(16, 20.9, color="#e3efff")
    ax.set_title(f"{kind}: % change after opening, by hour (weekdays)"); ax.set_xlabel("hour")
axes[0].set_ylabel("% change, post vs pre"); axes[0].legend()
PL.save_fig(fig, "fig4_hourly_signature.png")

# %% [markdown]
# ## 2 · Persistence into September
# Pre = 1–10 Aug; post = 1–30 Sep. Hours before 7 am are dropped (first train moved to 6:00 on 10 Sep).

# %%
days = C.PRE_DAYS + C.SEP_DAYS
sep = P.station_panel(days, stations=olds)
sep = sep[sep.hour >= 7]
sep["post"] = sep.date.isin(C.SEP_DAYS).astype(int)
sep = P.attach_exposure(sep, scores, "station", transfer=transfer)
rows = []
for kind in ("lentries", "lexits"):
    for x, lab in (("post_zYellowLink_s", "per SD YellowLink"), ("post_transfer_s", "transfer stations")):
        rows.append(E.tidy(E.fit(sep, kind, [x], ["fe_s_h", "fe_t_h"], "station"), f"{kind} · {lab}"))
pers = pd.concat(rows, ignore_index=True); PL.save_table(pers, "september_persistence.csv")
# week-by-week
sep["week"] = np.where(sep.post == 0, "pre", "Sep_w" + ((pd.to_datetime(sep.date).dt.day - 1) // 7 + 1).astype(str))
wk = []
for w in sorted(sep.week.unique()):
    if w == "pre": continue
    sep[f"w_{w}"] = (sep.week == w) * sep.transfer_s
wcols = [c for c in sep.columns if c.startswith("w_Sep")]
mw = E.fit(sep, "lexits", wcols, ["fe_s_h", "fe_t_h"], "station")
wk = E.tidy(mw, "lexits by week · transfer stations"); PL.save_table(wk, "september_by_week.csv")
pers[["model", "term", "Estimate", "Std. Error", "Pr(>|t|)"]].round(4)

# %% [markdown]
# ## 3 · Headway cut on 10 Sep (25 → 19 min)
# Difference-in-differences on September station-hour entries: new Yellow stations vs old stations,
# before vs after 10 Sep. Elasticity = β / ln(25/19). Hours before 7 am dropped.

# %%
hw = P.station_panel(C.SEP_DAYS)
hw = hw[hw.hour >= 7].copy()
hw["yellow"] = hw.station.isin(C.YELLOW_NEW).astype(int)
hw["post_hw"] = (hw.date >= C.HEADWAY_CUT_DATE).astype(int)
hw["treat"] = hw.yellow * hw.post_hw
# feeder split: Yellow stations whose nearby bus trips grew between the Aug and Sep snapshots
sup = pd.concat([PL.get_scores(C.SNAPSHOT_BEFORE).assign(t="before"), PL.get_scores(C.SNAPSHOT_AFTER).assign(t="after")])
bt = sup.pivot_table(index="station", columns="t", values="BusTrips")
feeder = bt.index[(bt["after"] > bt["before"])].intersection(C.YELLOW_NEW)
print("Yellow stations with more bus trips in Sep:", list(feeder))
hw["treat_feeder"] = hw.treat * hw.station.isin(feeder)
dln = np.log(C.HEADWAY_BEFORE / C.HEADWAY_AFTER)
rows = []
for kind in ("lentries", "lexits"):
    m = E.fit(hw, kind, ["treat"], ["fe_s_h", "fe_t_h"], "station")
    t = E.tidy(m, f"{kind} · Yellow x after 10 Sep"); t["elasticity"] = t.Estimate / dln; rows.append(t)
    m2 = E.fit(hw, kind, ["treat", "treat_feeder"], ["fe_s_h", "fe_t_h"], "station")
    rows.append(E.tidy(m2, f"{kind} · with feeder interaction"))
hwt = pd.concat(rows, ignore_index=True); PL.save_table(hwt, "headway_did.csv")
hwt[["model", "term", "Estimate", "Std. Error", "Pr(>|t|)", "elasticity"]].round(4)

# %%
# Event study by day (reference 9 Sep) and synthetic control on daily Yellow entries
hw["yellow_z"] = hw.yellow.astype(float)
es = E.event_study(hw, "lentries", "yellow_z", ["fe_s_h", "fe_t_h"], "station", ref="2025-09-09")
PL.save_table(es, "headway_event_study.csv")
daily = P.station_panel(C.SEP_DAYS).query("hour >= 7").groupby(["date", "station"]).entries.sum().unstack()
treated = np.log(daily[C.YELLOW_NEW].sum(axis=1))
donors = np.log(daily[[s for s in olds]].clip(lower=1))
pre_idx = [d for d in daily.index if d < C.HEADWAY_CUT_DATE]
# demeaned synthetic control: match the pre-period *shape* (log deviations from each unit's pre mean)
treated = treated - treated.loc[pre_idx].mean()
donors = donors - donors.loc[pre_idx].mean()
scm = E.synthetic_control(treated, donors, pre_idx)
post_gap = scm["gap"].loc[[d for d in daily.index if d >= C.HEADWAY_CUT_DATE]].mean()
print(f"synthetic control: pre RMSPE {scm['pre_rmspe']:.4f}; mean post gap {post_gap:.4f} log points "
      f"-> elasticity {post_gap / dln:.3f}")
PL.save_table(scm["weights"].reset_index().rename(columns={"index": "station", 0: "weight"}), "headway_synth_weights.csv")
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
x = pd.to_datetime(es.date)
axes[0].errorbar(x, es.Estimate, yerr=1.96 * es["Std. Error"], fmt="o", capsize=3, c="#d9a400")
axes[0].axhline(0, c="k", lw=0.6); axes[0].axvline(pd.Timestamp(C.HEADWAY_CUT_DATE) - pd.Timedelta(hours=12), ls="--", c="k")
axes[0].set_title("Yellow vs old stations, log entries (ref 9 Sep)"); axes[0].tick_params(axis="x", rotation=45)
xd = pd.to_datetime(treated.index)
axes[1].plot(xd, treated.values, c="#d9a400", lw=2, label="Yellow stations (actual)")
axes[1].plot(xd, scm["synthetic"].values, c="#555", ls="--", label="synthetic control")
axes[1].axvline(pd.Timestamp(C.HEADWAY_CUT_DATE), ls="--", c="k"); axes[1].legend(); axes[1].tick_params(axis="x", rotation=45)
axes[1].set_title("Daily Yellow entries (log), 7 am onward")
PL.save_fig(fig, "fig5_headway.png")
