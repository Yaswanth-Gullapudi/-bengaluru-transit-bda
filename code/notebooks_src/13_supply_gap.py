"""13 - Supply gap: where forecast metro demand is high but bus service is thin, and what fixes it.

Runs locally on outputs already produced by notebooks 10, 11 and 12 (no Kaggle run needed).
  1. Gap finder   : forecast metro entries per station-hour (notebook 11, test week 22-30 Sep 2025)
                    divided by weekday bus trips stopping within 400 m in that hour (notebook 10, GTFS 4 Aug 2025).
  2. Bus fix      : dedicated metro-feeder trips per hour needed at each gap station-hour, under stated planning
                    assumptions (share of metro riders arriving by bus: 10% / 20%; 50 metro riders per feeder trip).
                    We have no bus ridership, so this is a sizing scenario, not a measured effect.
  3. Train fix    : Yellow Line headway scenarios from the measured frequency elasticity (0.21-0.30, notebook 05/10)
                    and the average Yellow fare (notebook 12).
All thresholds are stated in the outputs. Results are planning estimates, not causal effects of buses.
"""
import json, math, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = pathlib.Path(__file__).resolve().parents[2]          # repository root
K = next((R / d for d in ("results", "kaggle_results_acc2") if (R / d).exists()), R / "results")
OUT = next((R / d for d in ("extensions/outputs", "work_ext/outputs") if (R / d).exists()), R / "extensions/outputs")
TAB, FIG = OUT / "tables", OUT / "figures"
TAB.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)

CROWD = 1637                 # crowding threshold from notebook 11 (busiest 5% of station-hours)
PEAK = [7, 8, 9, 17, 18, 19]  # weekday peak hours
MIN_DEMAND = 1000            # busy station-hours only (forecast entries per hour)
SHARES = (0.10, 0.20)        # assumed share of metro riders arriving by bus (scenario)
LOAD = 50                    # assumed metro riders carried per feeder trip

# ------------------------------------------------------------------ inputs
pred = pd.read_csv(K / "11/outputs/tables/forecast_test_predictions.csv")
pred["date"] = pd.to_datetime(pred["date"])
pred = pred[pred["date"].dt.dayofweek < 5]                       # weekdays: 22-26, 29, 30 Sep
bus = (pd.read_csv(TAB / "bus_station_hourly.csv").melt(id_vars="station", var_name="hour", value_name="bus_trips"))
bus["hour"] = bus["hour"].astype(int)
lines = pd.read_csv(TAB / "integration_index.csv")[["station", "line"]]

# average weekday station-hour: forecast, actual, buses
sh = (pred.groupby(["station", "hour"])
          .agg(forecast_entries=("pred", "mean"), actual_entries=("entries", "mean"),
               forecast_hi=("hi", "mean"), crowded_days=("pred", lambda s: int((s > CROWD).sum())))
          .reset_index()
          .merge(bus, on=["station", "hour"], how="left")
          .merge(lines, on="station", how="left"))
sh["bus_trips"] = sh["bus_trips"].fillna(0)
sh["has_bus_data"] = sh["station"].isin(bus["station"].unique())
sh["riders_per_bus_forecast"] = sh["forecast_entries"] / sh["bus_trips"].clip(lower=1)
sh["riders_per_bus_actual"] = sh["actual_entries"] / sh["bus_trips"].clip(lower=1)

# ------------------------------------------------------------------ 1. gap finder
peak = sh[sh["hour"].isin(PEAK) & (sh["forecast_entries"] >= MIN_DEMAND) & sh["has_bus_data"]]
bench = float(peak["riders_per_bus_forecast"].median())        # typical metro riders per bus trip at peak
cand = sh[(sh["forecast_entries"] >= MIN_DEMAND) & sh["has_bus_data"]].copy()
cand["gap_ratio"] = cand["riders_per_bus_forecast"] / bench
cand = cand.sort_values("riders_per_bus_forecast", ascending=False)

# validation: are the forecast's top gaps also the top gaps in what actually happened?
TOPN = 20
top_f = set(map(tuple, cand.head(TOPN)[["station", "hour"]].values))
act = cand.sort_values("riders_per_bus_actual", ascending=False)
top_a = set(map(tuple, act.head(TOPN)[["station", "hour"]].values))
overlap = len(top_f & top_a)
rho = cand[["riders_per_bus_forecast", "riders_per_bus_actual"]].corr(method="spearman").iloc[0, 1]

# ------------------------------------------------------------------ 2. bus fix (feeder sizing scenario)
for sh_ in SHARES:
    cand[f"feeder_trips_per_hour_{int(sh_*100)}pct"] = np.ceil(sh_ * cand["forecast_entries"] / LOAD).astype(int)
cand["extra_bus_trips_per_hour"] = cand[f"feeder_trips_per_hour_{int(SHARES[0]*100)}pct"]
cand["feeder_headway_min_10pct"] = (60 / cand["feeder_trips_per_hour_10pct"]).round(1)
cand["crowding_warning"] = cand["forecast_entries"] > CROWD
feed = pd.read_csv(TAB / "integration_index.csv")[["station", "feeder_trips"]]
cand = cand.merge(feed, on="station", how="left").rename(columns={"feeder_trips": "current_feeder_trips_per_day"})
cand = cand.sort_values("riders_per_bus_forecast", ascending=False)
def action(r):
    acts = []
    if r["gap_ratio"] >= 2:
        acts.append(f"feeder bus every {r['feeder_headway_min_10pct']:g} min ({r['feeder_trips_per_hour_10pct']}-{r['feeder_trips_per_hour_20pct']} trips/h)")
    if r["crowding_warning"]:
        acts.append(f"add trains on {r['line']} line this hour")
    return "; ".join(acts) if acts else "no change"
cand["recommended_action"] = cand.apply(action, axis=1)
gap_list = cand[cand["gap_ratio"] >= 2].copy()

stations = (gap_list.groupby(["station", "line"])
            .agg(gap_hours=("hour", "size"), worst_hour=("hour", lambda h: int(h.iloc[0])),
                 peak_forecast_entries=("forecast_entries", "max"),
                 feeder_trips_gap_hours_10pct=("feeder_trips_per_hour_10pct", "sum"),
                 feeder_trips_gap_hours_20pct=("feeder_trips_per_hour_20pct", "sum"),
                 current_feeder_trips_per_day=("current_feeder_trips_per_day", "first"))
            .reset_index().sort_values("gap_hours", ascending=False))
# stations with no bus stop at all within 400 m (cannot be fixed by frequency alone)
nobus = (sh[sh["has_bus_data"]].groupby("station")["bus_trips"].sum())
nobus = sorted(nobus[nobus == 0].index)
missing = sorted(set(sh["station"]) - set(bus["station"]))

# ------------------------------------------------------------------ 3. train fix (Yellow Line headway scenarios)
hw = pd.read_csv(K / "12/outputs/tables/fare_headway.csv").iloc[0]
base_entries = float(hw["yellow_weekday_entries_before_cut"]) * (1 + float(hw["did_entry_effect"]))  # after the 19-min cut
fare = float(hw["yellow_origin_avg_fare"])
rows = []
for H in [19, 15, 12, 10, 8]:
    for eps, lab in [(0.21, "low (synthetic control)"), (0.30, "high (DiD)")]:
        gain = (19 / H) ** eps - 1
        rows.append({"headway_min": H, "trains_per_hour": round(60 / H, 1), "extra_trains_per_hour": round(60 / H - 60 / 19, 1),
                     "elasticity": eps, "elasticity_source": lab, "entries_change_pct": 100 * gain,
                     "extra_entries_per_weekday": base_entries * gain,
                     "extra_revenue_per_weekday_rs": base_entries * gain * fare,
                     "extra_revenue_per_year_rs": base_entries * gain * fare * 250,
                     "within_observed_range": H >= 19})
trains = pd.DataFrame(rows)

# ------------------------------------------------------------------ 4. verdict per busy station-hour
# more buses : bus gap (>= 2x the typical busy-hour riders per bus trip)
# more trains: crowding warning (forecast > 1,637 entries/h, the busiest 5% of station-hours)
VERDICTS = ["More buses and trains", "More buses", "More trains", "OK"]
def verdict(r):
    b, t = r["gap_ratio"] >= 2, bool(r["crowding_warning"])
    return VERDICTS[0] if b and t else VERDICTS[1] if b else VERDICTS[2] if t else VERDICTS[3]
cand["verdict"] = cand.apply(verdict, axis=1)
vcount = cand["verdict"].value_counts().reindex(VERDICTS, fill_value=0)
vstation = (cand[cand["verdict"] != "OK"].groupby(["station", "line", "verdict"])["hour"]
            .apply(lambda h: ", ".join(f"{int(x):02d}" for x in sorted(h))).reset_index(name="hours"))
vstation["order"] = vstation["verdict"].map({v: i for i, v in enumerate(VERDICTS)})
vstation = vstation.sort_values(["order", "station"]).drop(columns="order")
vstation.to_csv(TAB / "supply_verdict_stations.csv", index=False)

# ------------------------------------------------------------------ save tables
cols = ["station", "line", "hour", "forecast_entries", "actual_entries", "bus_trips", "riders_per_bus_forecast",
        "riders_per_bus_actual", "gap_ratio", "feeder_trips_per_hour_10pct", "feeder_trips_per_hour_20pct",
        "feeder_headway_min_10pct", "current_feeder_trips_per_day", "crowding_warning", "crowded_days", "verdict",
        "recommended_action"]
cand[cols].to_csv(TAB / "supply_gap_station_hours.csv", index=False)
gap_list = cand[cand["gap_ratio"] >= 2].copy()
gap_list[cols].to_csv(TAB / "supply_gap_list.csv", index=False)
stations.to_csv(TAB / "supply_gap_stations.csv", index=False)
trains.to_csv(TAB / "train_headway_scenarios.csv", index=False)
summary = {"test_weekdays": sorted(pred["date"].dt.strftime("%Y-%m-%d").unique().tolist()),
           "benchmark_riders_per_bus_trip_busy_peak": bench, "gap_rule": "forecast >= 1000 entries/h and riders per bus trip >= 2x benchmark",
           "feeder_assumptions": {"bus_access_share": list(SHARES), "metro_riders_per_feeder_trip": LOAD},
           "gap_station_hours": int(len(gap_list)), "gap_stations": int(gap_list["station"].nunique()),
           "feeder_trips_per_weekday_gap_hours_10pct": int(gap_list["feeder_trips_per_hour_10pct"].sum()),
           "feeder_trips_per_weekday_gap_hours_20pct": int(gap_list["feeder_trips_per_hour_20pct"].sum()),
           "crowded_station_hours_forecast": int(cand["crowding_warning"].sum()),
           f"top{TOPN}_overlap_forecast_vs_actual": overlap, "spearman_forecast_vs_actual_riders_per_bus": float(rho),
           "stations_with_no_bus_within_400m": nobus, "stations_without_bus_data": missing,
           "yellow_base_weekday_entries_after_cut": base_entries, "yellow_avg_fare_rs": fare,
           "verdict_rule": {"More buses": "riders per bus trip >= 2x benchmark", "More trains": f"forecast > {CROWD} entries/h"},
           "verdict_counts_busy_station_hours": {k: int(v) for k, v in vcount.items()},
           "busy_station_hours": int(len(cand))}
(TAB / "supply_gap_summary.json").write_text(json.dumps(summary, indent=2))

# ------------------------------------------------------------------ figure
fig, ax = plt.subplots(1, 2, figsize=(13, 5.2), dpi=180, gridspec_kw={"width_ratios": [1.25, 1]})
top = cand.head(15).iloc[::-1]
xmax = 140
labels = [f"{s} {h:02d}:00" for s, h in zip(top["station"], top["hour"])]
ax[0].barh(labels, top["riders_per_bus_forecast"].clip(upper=xmax), color="#2166AC")
ax[0].axvline(bench, color="#B2182B", ls="--", lw=1.2)
ax[0].text(bench + 2, len(top) - 0.45, f"typical busy hour = {bench:.0f}", color="#B2182B", fontsize=8, va="bottom")
for i, (v, e, b) in enumerate(zip(top["riders_per_bus_forecast"], top["extra_bus_trips_per_hour"], top["bus_trips"])):
    off = f" (off scale: {v:,.0f})" if v > xmax else ""
    ax[0].text(min(v, xmax), i, f"  {int(b)} bus trips/h · feeder {e}/h{off}", va="center", fontsize=7.5)
ax[0].set_xlabel("forecast metro entries per bus trip within 400 m")
ax[0].set_title("Biggest bus gaps, forecast weekdays 22-30 Sep", fontsize=10)
ax[0].set_xlim(0, xmax * 1.9); ax[0].set_ylim(-0.6, len(top) + 0.4)
for eps, c in [(0.21, "#92C5DE"), (0.30, "#2166AC")]:
    t = trains[trains["elasticity"] == eps]
    ax[1].plot(t["headway_min"], t["extra_entries_per_weekday"], marker="o", color=c, label=f"elasticity {eps}")
ax[1].invert_xaxis()
ax[1].axvspan(19, 25, color="#EEEEEE", zorder=0)
ax[1].text(22, ax[1].get_ylim()[1] * 0.92 if ax[1].get_ylim()[1] > 0 else 1, "measured\n25→19 min", ha="center", fontsize=8, color="#555555")
ax[1].set_xlabel("Yellow Line headway (minutes)"); ax[1].set_ylabel("extra weekday entries vs 19 min")
ax[1].set_title("More trains: Yellow Line headway scenarios", fontsize=10)
ax[1].legend(fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(FIG / "fig21_supply_gap.png", facecolor="white")
print(json.dumps(summary, indent=2))
print(cand.head(15)[["station", "line", "hour", "forecast_entries", "actual_entries", "bus_trips",
                     "riders_per_bus_forecast", "feeder_trips_per_hour_10pct", "feeder_trips_per_hour_20pct", "recommended_action"]].to_string())
print(stations.head(12).to_string())
print(trains.round(1).to_string())

# ------------------------------------------------------------------ figure: verdict heatmap (stations that need something)
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
VCOL = {"More buses and trains": "#762A83", "More buses": "#E08214", "More trains": "#2166AC", "OK": "#D9D9D9"}
code = {v: i for i, v in enumerate(VERDICTS)}
need = cand[cand["verdict"] != "OK"]
order = (need.assign(o=need["verdict"].map(code)).groupby("station")["o"].min().reset_index()
         .merge(need.groupby("station").size().rename("n").reset_index(), on="station")
         .sort_values(["o", "n"], ascending=[True, False])["station"].tolist())
hours = list(range(6, 23))
grid = np.full((len(order), len(hours)), np.nan)
for _, r in cand[cand["station"].isin(order)].iterrows():
    if r["hour"] in hours:
        grid[order.index(r["station"]), hours.index(r["hour"])] = code[r["verdict"]]
short = {"Nadaprabhu Kempegowda Station, Majestic": "Majestic", "Dr. B. R. Ambedkar Station, Vidhana Soudha": "Vidhana Soudha",
         "Sir M. Visvesvaraya Stn., Central College": "Central College", "Krantivira Sangolli Rayanna Railway Station": "KSR Railway Stn.",
         "Sri Balagangadharanatha Swamiji Station, Hosahalli": "Hosahalli", "Mahatma Gandhi Road": "MG Road",
         "Mantri Square Sampige Road": "Sampige Road"}
fig, ax = plt.subplots(figsize=(11, 0.34 * len(order) + 1.6), dpi=180)
ax.imshow(np.ma.masked_invalid(grid), cmap=ListedColormap([VCOL[v] for v in VERDICTS]), vmin=-0.5, vmax=3.5, aspect="auto")
ax.set_xticks(range(len(hours))); ax.set_xticklabels([f"{h:02d}" for h in hours], fontsize=8)
ax.set_yticks(range(len(order))); ax.set_yticklabels([short.get(s, s) for s in order], fontsize=8)
ax.set_xticks(np.arange(-.5, len(hours)), minor=True); ax.set_yticks(np.arange(-.5, len(order)), minor=True)
ax.grid(which="minor", color="white", lw=1.2); ax.tick_params(which="minor", length=0)
ax.set_xlabel("hour of day (forecast weekdays 22-30 Sep 2025; blank = under 1,000 forecast entries)", fontsize=8.5)
ax.set_title("What each busy station-hour needs", fontsize=10)
ax.legend(handles=[Patch(color=VCOL[v], label=f"{v} ({int(vcount[v])})") for v in VERDICTS],
          loc="upper center", bbox_to_anchor=(0.5, -0.045), ncol=4, fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(FIG / "fig22_verdict.png", facecolor="white")
print(vcount.to_string()); print(vstation.to_string())
