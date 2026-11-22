# %% [markdown]
# # 10 · Extensions and all lines
# * **Pink Line pre-registration** (second event, opened 14 Nov 2026): bus-link scores from the 9 Nov 2026 GTFS, top 10 frozen and hashed.
# * **Feeder maturity**, **heterogeneity** (for whom), **pair-level substitution**, **observational vs causal**, **second shock** (10 Sep headway cut), **sensitivity** (incomplete trips, straight-line catchment), **bus speeds**.
# * **All lines:** bus-metro integration index for every station, line-by-line demand, opening effect by line.
# * **New-station prediction with Spark MLlib:** unseen-station cross-validation and the 15 Yellow stations.

# %%
SETUP

# %%
from t15 import extensions as X, lines as L, bus as B, panels as P, econ as E, env
import pandas as pd, numpy as np, matplotlib.pyplot as plt
scores = PL.get_scores(); transfer = PL.get_transfer_list(); pop = PL.get_population(800)
router = PL.router()
cols = ["model", "term", "Estimate", "Std. Error", "Pr(>|t|)"]

# %% [markdown]
# ## Pink Line pre-registration and feeder maturity

# %%
ps = X.pink_scores(router=router); PL.save_table(ps, "pink_station_scores.csv")
f = PL.find_output("frozen_pink_stations.json")
rec = __import__("json").loads(f.read_text()) if f is not None else X.freeze_pink(ps)   # keep the first frozen list
print(rec)
fs = X.feeder_summary(["2024-01-05", "2025-08-04", "2025-09-02", "2026-11-09"]); PL.save_table(fs, "feeder_summary.csv"); fs

# %% [markdown]
# ## Heterogeneity, pair substitution, observational vs causal, second shock

# %%
panel = P.attach_exposure(P.od_panel(D.load_od(), by="band"), scores, "dest", transfer=transfer)
FE = ["fe_o_t", "fe_o_d"]
chars = X.origin_characteristics(scores, pop)
het = X.heterogeneity(panel, chars, FE); PL.save_table(het, "heterogeneity.csv")
pr, summ = X.pair_substitution(panel, FE); PL.save_table(pr, "pair_substitution.csv")
obs = X.observational_cross_section(scores, pop); PL.save_table(obs, "observational_cross_section.csv")
hs = X.headway_shock_on_old(scores, transfer); PL.save_table(hs, "headway_shock_old_stations.csv")
pd.concat([het[cols], pr[cols], hs[cols]]).round(4)

# %%
obs.round(4)

# %% [markdown]
# ## Sensitivity: incomplete trips and straight-line catchment

# %%
rows = []
for label, sc in (("score without 1-2 stop trips", B.station_scores(C.SNAPSHOT_BEFORE, router=router, min_trip_stops=3)),
                  ("straight-line catchment score", B.station_scores(C.SNAPSHOT_BEFORE, use_osm=False))):
    p2 = P.attach_exposure(panel.drop(columns=[c for c in panel.columns if "YellowLink" in c]), sc, "dest", cols=("YellowLink",))
    rows.append(E.tidy(E.fit(p2, "ltrips", ["post_zYellowLink_d"], FE, "dest"), label))
sens = pd.concat(rows); PL.save_table(sens, "sensitivity_scores.csv"); sens[cols].round(4)

# %% [markdown]
# ## Bus speeds

# %%
trip, sp = X.scheduled_speeds(); PL.save_table(sp, "bus_scheduled_speed_by_hour.csv")
print("median scheduled speed km/h:", round(trip.kmh.median(), 1))

# %% [markdown]
# ## All lines: integration index, demand, opening effect by line

# %%
bh, bt = L.bus_station_hourly(C.SNAPSHOT_BEFORE, None)
A = L.integration_index(scores, bt, pop); PL.save_table(A.reset_index(), "integration_index.csv")
A.sort_values("gap", ascending=False).head(10)

# %%
Bd = L.line_demand()
for k, v in Bd.items(): PL.save_table(v.reset_index(), f"line_demand_{k}.csv")
Ct, Co = L.opening_effect_by_line(scores); PL.save_table(Ct, "opening_effect_by_line_od.csv"); PL.save_table(Co.reset_index(), "opening_effect_by_origin_line.csv")
Co.round(1)

# %%
fig, ax = plt.subplots(1, 2, figsize=(15, 5))
colors = {"Purple": "#7d2a6e", "Green": "#13894a", "Yellow": "#e0b400", "Interchange (Majestic)": "#555", "Interchange (RV Road)": "#999"}
for line, g in A.groupby("line"):
    ax[0].scatter(g.integration_index, np.log10(g.sep_daily_entries), color=colors.get(line, "k"), label=line, s=30)
for s, r in A.sort_values("gap", ascending=False).head(6).iterrows():
    ax[0].annotate(s.replace("Nadaprabhu Kempegowda Station, ", ""), (r.integration_index, np.log10(r.sep_daily_entries)), fontsize=7)
ax[0].set_xlabel("bus-metro integration index (z)"); ax[0].set_ylabel("log10 September weekday entries"); ax[0].legend(fontsize=8)
ax[0].set_title("Busy stations with weak bus links (top left)")
h = Bd["hourly"].loc["September"]
for line in ("Purple", "Green", "Yellow"):
    ax[1].plot(h.columns, h.loc[line] / h.loc[line].sum(), label=line, color=colors[line])
ax[1].set_title("Share of daily entries by hour, September weekdays"); ax[1].set_xlabel("hour"); ax[1].legend()
PL.save_fig(fig, "fig18_all_lines.png")

# %% [markdown]
# ## New-station prediction (Spark MLlib)

# %%
spark = env.start(cores=4, memory="20g", hdfs=False)
tab = L.new_station_table(scores, bh, bt, pop)
ny = L.new_station_ml(spark, tab); PL.save_table(ny, "new_station_ml.csv")
cv = L.unseen_station_cv(spark, tab); PL.save_table(cv, "unseen_station_cv.csv")
pd.concat([ny.assign(test="15 new Yellow stations"), cv.assign(test="68 unseen old stations (5-fold)")]).round(3)

# %%
spark.stop()
