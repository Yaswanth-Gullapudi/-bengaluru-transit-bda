# %% [markdown]
# # 01 · Bus-link score and the frozen list of bus-transfer stations
# For every metro station we measure, from the **4 Aug 2025** BMTC network (one week before the
# Yellow Line opened), how strongly its nearby buses connected to the new Yellow corridor.
#
# | Measure | Definition |
# |---|---|
# | `BusTrips` | weekday bus trips stopping within **400 m walk** of the station's entrances |
# | `YellowLink` | share of those trips that also stop within **800 m walk** of a new Yellow station |
# | `YellowLinkDir` | same, counting only trips that reach the corridor *after* the station (towards it) |
# | `Collinear` | mean number of corridor stops each of those trips visits (route overlap) |
# | `MetroHopsToRV` | metro stations travelled to RV Road (from the BMRCL fare table) |
#
# Walking distances use the OpenStreetMap footpath network, starting from each station's mapped entrances.
#
# **Pre-registration.** The 10 bus-transfer stations are chosen by a fixed rule *before any ridership
# is analysed*. The list is written with a UTC timestamp and SHA-256 hash; upload
# `outputs/preregistration.md` and `frozen_transfer_stations.json` to OSF (osf.io → New project →
# Registrations) **before running notebook 02**.

# %%
SETUP

# %%
from t15 import bus as B
import pandas as pd, numpy as np, matplotlib.pyplot as plt

scores = {}
for snap in (C.SNAPSHOT_BEFORE, C.SNAPSHOT_AFTER):
    for cm, ym in ((400, 800), (800, 800), (400, 400)):
        scores[(snap, cm, ym)] = PL.get_scores(snap, cm, ym)
        print(snap, cm, ym, "done")
sc = scores[(C.SNAPSHOT_BEFORE, 400, 800)]
cols = ["station", "lines", "BusTrips", "BusRoutes", "YellowLink", "YellowLinkDir", "Collinear",
        "near_corridor", "MetroHopsToRV", "osm_walk"]
sc[~sc.is_yellow_new].sort_values("YellowLink", ascending=False)[cols].head(20)

# %% [markdown]
# ## Freeze the bus-transfer stations (no ridership used)

# %%
top = B.freeze_transfer_list(sc)
print(open(C.paths()["out"] / "frozen_transfer_stations.json").read())
top[cols]

# %%
# Pre-registration document for OSF
import json, datetime
rec = json.loads(open(C.paths()["out"] / "frozen_transfer_stations.json").read())
prereg = f"""# Pre-registration: Yellow Line opening and bus-mediated metro ridership (Team 15)

Created (UTC): {rec['created_utc']}
SHA-256 of frozen list record: {rec['sha256']}

## Hypotheses
H1 (diversion). From the same origin, trips to stations with a high bus link to the Yellow corridor
(YellowLink, BMTC GTFS 4 Aug 2025) fall after 11 Aug 2025 relative to other destinations.
H2 (matching). Origins that lose the most share to the frozen bus-transfer stations gain the most share to new Yellow stations.
H3 (time-of-day). At the frozen bus-transfer stations, AM-peak exits and PM-peak entries fall more than midday counts.

## Frozen bus-transfer stations
Rule: {rec['rule']}
Stations: {', '.join(rec['stations'])}

## Primary specification
Data: BMRCL station-pair hourly ridership, 1-18 Aug 2025, old stations only, aggregated to
date x time band (am_peak 7-10, midday 11-15, pm_peak 16-20, other).
Model: log(1+trips[o,d,date,band]) = FE[o x date x band] + FE[o x d x band] + b * post x zYellowLink_d + e
Inference: SE clustered by destination; wild-cluster bootstrap (Webb) and randomisation inference (1,000 permutations).
Secondary: PPML on counts; binary post x transfer_d; event study by day (reference 7 Aug).

## Pre-specified robustness
Placebo opening dates 5 and 7 Aug; drop 15-16 Aug; drop Lalbagh and Mahalakshmi; drop 11-12 Aug;
controls post x MetroHopsToRV_d, post x line_d, post x BusTrips_d; within-line samples;
400 vs 800 m catchments; exposure from the 2 Sep 2025 snapshot; hourly instead of bands.
"""
(C.paths()["out"] / "preregistration.md").write_text(prereg)
print(prereg)

# %% [markdown]
# ## How the scores relate to each other (and to plain geography)

# %%
old = sc[~sc.is_yellow_new & (sc.station != C.INTERCHANGE)]
corr = old[["YellowLink", "YellowLinkDir", "Collinear", "BusTrips", "MetroHopsToRV"]].corr(method="spearman")
PL.save_table(corr.reset_index(), "score_correlations_spearman.csv")
corr.round(2)

# %%
# Stability of the score across catchment sizes and snapshots
cmp = pd.DataFrame({f"{k[0]} c{k[1]} y{k[2]}": v.set_index("station")["YellowLink"] for k, v in scores.items()})
cmp.loc[old.station].corr(method="spearman").round(2)

# %% [markdown]
# ## Figure 1 · Map of metro stations coloured by YellowLink

# %%
D_st = D.metro_stations()
ya = D.yellow_alignment()
fig, ax = plt.subplots(figsize=(8, 9))
g = D.load_gtfs(C.SNAPSHOT_BEFORE, tables=("stops",))["stops"]
ax.scatter(g.stop_lon, g.stop_lat, s=0.3, c="#bbbbbb", label="BMTC stops")
ax.plot(ya.lon, ya.lat, "-", c="#d9a400", lw=3, label="Yellow Line (new)")
m = sc.merge(D_st[["station"]], on="station")
o = m[~m.is_yellow_new]
p = ax.scatter(o.lon, o.lat, c=o.YellowLink, cmap="viridis", s=60, edgecolor="k", zorder=3)
ax.scatter(m[m.station.isin(rec["stations"])].lon, m[m.station.isin(rec["stations"])].lat,
           s=220, facecolor="none", edgecolor="crimson", lw=2, zorder=4, label="frozen bus-transfer stations")
for _, r in m[m.station.isin(rec["stations"])].iterrows():
    ax.annotate(r.station.split(",")[0], (r.lon, r.lat), xytext=(5, 5), textcoords="offset points", fontsize=7)
plt.colorbar(p, ax=ax, shrink=0.6, label="YellowLink (share of nearby bus trips reaching the corridor)")
ax.set_xlim(77.44, 77.80); ax.set_ylim(12.78, 13.08); ax.set_aspect("equal")
ax.legend(loc="upper right", fontsize=8); ax.set_title("Bus links from metro stations to the Yellow corridor (BMTC, 4 Aug 2025)")
PL.save_fig(fig, "fig1_yellowlink_map.png")
