# %% [markdown]
# # 08 · Who gained? Population, wards and bus access
# **Data**
# * RAS-PT polling-booth polygons (urbanmorph/RAS-PT, shown on bmtc.vonter.top/bus_stops_accessibility):
#   2022 electoral-roll population and 2018 bus-stop access for every booth in 29 assembly constituencies.
# * OpenCity *BMTC Bus Stops and Routes Map by Ward* (dataset `t15-ward`): per-constituency CSVs of 2018
#   stops with trip counts. Results are summarised by assembly constituency (AC 150–177).
#
# **Questions**
# 1. How many people gained **direct** metro access (≤ 800 m from a new Yellow station)?
# 2. How many more are within 400 m of a bus stop with a trip to the corridor (a **bus link**)?
# 3. How has bus access changed between the 2018 network (RAS-PT) and the 2025 GTFS?

# %%
SETUP

# %%
from t15 import wards as W
import pandas as pd, numpy as np, matplotlib.pyplot as plt
booths = D.load_booths()
print(booths.shape, "booths |", int(booths.people.sum()), "people |", booths.ac_name.nunique(), "constituencies")
pop = PL.get_population(800); PL.get_population(400)
pop.sort_values(ascending=False).head(10)

# %%
acc = W.booth_access(booths)
PL.save_table(acc, "booth_access.csv")
tot = acc.people.sum()
summary = pd.DataFrame([{
    "people_total": tot,
    "within_800m_metro_before": acc.loc[acc.metro_before, "people"].sum(),
    "within_800m_metro_after": acc.loc[acc.metro_after, "people"].sum(),
    "gained_direct_access": acc.loc[acc.gained_direct_metro, "people"].sum(),
    "bus_link_to_yellow_400m": acc.loc[acc.bus_link_yellow, "people"].sum(),
    "bus_link_only_no_direct": acc.loc[acc.bus_link_yellow & ~acc.metro_after, "people"].sum(),
}])
PL.save_table(summary, "access_summary.csv")
summary.T.assign(share=lambda d: d[0] / tot)

# %%
area = W.area_summary(acc)
PL.save_table(area, "area_summary.csv")
area.head(15)

# %% [markdown]
# ## Figure 11 · Booths that gained direct access vs bus-linked only

# %%
st = D.metro_stations(); ya = D.yellow_alignment()
fig, ax = plt.subplots(figsize=(8, 9))
ax.scatter(acc.lon, acc.lat, s=2, c="#dddddd")
bl = acc[acc.bus_link_yellow & ~acc.metro_after]
ax.scatter(bl.lon, bl.lat, s=3, c="#1f6fb2", label="bus link to Yellow only (≤400 m to a linking stop)")
gd = acc[acc.gained_direct_metro]
ax.scatter(gd.lon, gd.lat, s=4, c="#d9a400", label="gained direct metro access (≤800 m)")
ax.plot(ya.lon, ya.lat, "-", c="#a57d00", lw=2)
ax.scatter(st.lon, st.lat, s=12, c="k", zorder=3)
ax.set_xlim(77.44, 77.80); ax.set_ylim(12.78, 13.10); ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=8)
ax.set_title("Polling booths (2022 population) by access to the Yellow Line")
PL.save_fig(fig, "fig11_access_map.png")

# %% [markdown]
# ## BMTC service 2018 (OpenCity, myBMTC app) vs 2025 (GTFS), by constituency
# Each 2018 stop is matched to the nearest 2025 GTFS stop within 100 m; trips per weekday are compared
# at matched stops. Also a data-quality check: how many 2018 stops still exist in 2025.

# %%
svc = W.ac_service_change()
if svc is not None:
    PL.save_table(svc, "ac_service_2018_vs_2025.csv")
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.barh(svc.ac_file, svc.trip_change_pct, color=np.where(svc.trip_change_pct < 0, "crimson", "#23924a"))
    ax.axvline(0, c="k", lw=0.6); ax.set_xlabel("% change in weekday bus trips at matched stops, 2018 → 2025")
    ax.set_title("BMTC service change by assembly constituency")
    PL.save_fig(fig, "fig12_service_change_by_ac.png")
    display(svc.round(3))

# %% [markdown]
# ## Bus access 2018 (RAS-PT) vs 2025 (GTFS), by constituency
# Caveat: the two measures are defined differently. RAS-PT 2018 = share of the booth's *area* within
# walking distance of a stop; 2025 = whether the booth's *centre* is within 400 m of a GTFS stop.
# Read the change as indicative, not exact.

# %%
g = D.load_gtfs(C.SNAPSHOT_BEFORE, tables=("stops",))["stops"]
from t15.bus import haversine
near = np.zeros(len(acc), bool)
for i in range(0, len(acc), 500):
    sl = slice(i, i + 500)
    d = haversine(acc.lat.values[sl, None], acc.lon.values[sl, None], g.stop_lat.values[None, :], g.stop_lon.values[None, :])
    near[sl] = d.min(axis=1) <= 400
acc["stop_within_400m_2025"] = near
cmp = acc.assign(w2025=acc.people * acc.stop_within_400m_2025, w2018=acc.people * acc.access_pct_2018.fillna(0) / 100) \
         .groupby("ac_name")[["people", "w2018", "w2025"]].sum()
cmp["access_2018"] = cmp.w2018 / cmp.people; cmp["access_2025"] = cmp.w2025 / cmp.people
cmp["change_pp"] = (cmp.access_2025 - cmp.access_2018) * 100
PL.save_table(cmp.reset_index(), "bus_access_2018_vs_2025.csv")
cmp.sort_values("change_pp")[["people", "access_2018", "access_2025", "change_pp"]].round(3)
