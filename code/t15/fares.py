"""Fare revenue (notebook 12): what the Yellow Line and the headway cut meant for BMRCL's fare box.

Uses the fare and revenue fields of the BMRCL station-pair data (1-18 Aug 2025) and the September
station entries. Revenue is fare-box money only: not profit (operating costs are not public) and not the
full economic gain (passengers' time savings are not counted).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from . import data as D

LINE = {"PURPLE": "Purple", "GREEN": "Green", "YELLOW": "Yellow", "GREEN+PURPLE": "Majestic", "GREEN+YELLOW": "RV Road"}


def _weekdays(days):
    return [d for d in days if pd.Timestamp(d).dayofweek < 5 and d not in C.EVENT_DAYS]


def fare_revenue(headway_effect: float = 0.087, weekdays_per_year: int = 250) -> dict:
    od = D.load_od()
    od = od[od["origin"] != od["dest"]].copy()
    st = D.metro_stations().set_index("station")
    od["origin_line"] = od["origin"].map(st["lines"]).map(LINE)
    pre, post = _weekdays(C.PRE_DAYS), _weekdays(C.POST_DAYS)
    od["period"] = np.select([od["date"].isin(pre), od["date"].isin(post)], ["before", "after"], "other")
    o = od[od["period"] != "other"].copy()
    nd = o.groupby("period")["date"].nunique()
    o["yellow_trip"] = o["origin"].isin(C.YELLOW_NEW) | o["dest"].isin(C.YELLOW_NEW)

    tot = o.groupby("period")[["trips", "revenue"]].sum().div(nd, axis=0)
    tot["avg_fare"] = tot["revenue"] / tot["trips"]
    rows = []
    for k, label in (("trips", "Trips per weekday"), ("revenue", "Fare revenue per weekday (Rs)"), ("avg_fare", "Average fare (Rs)")):
        rows.append({"measure": label, "before": tot.at["before", k], "after": tot.at["after", k],
                     "change_pct": (tot.at["after", k] / tot.at["before", k] - 1) * 100})
    old = o[~o["yellow_trip"]].groupby("period")["revenue"].sum() / nd
    rows.append({"measure": "Revenue from trips not using new stations (Rs)", "before": old["before"], "after": old["after"],
                 "change_pct": (old["after"] / old["before"] - 1) * 100})
    summary = pd.DataFrame(rows)

    yt = o[(o["period"] == "after") & o["yellow_trip"]]
    yellow = {"trips_per_weekday": yt["trips"].sum() / nd["after"], "revenue_per_weekday": yt["revenue"].sum() / nd["after"],
              "avg_fare": yt["revenue"].sum() / yt["trips"].sum(),
              "share_of_revenue_pct": yt["revenue"].sum() / o[o["period"] == "after"]["revenue"].sum() * 100}
    yellow["revenue_per_year_weekdays"] = yellow["revenue_per_weekday"] * weekdays_per_year

    by_line = o.groupby(["origin_line", "period"])[["trips", "revenue"]].sum().unstack("period").div(nd, level="period", axis=1)
    by_line.columns = [f"{a}_{b}" for a, b in by_line.columns]
    by_line["revenue_change_pct"] = (by_line["revenue_after"] / by_line["revenue_before"].replace(0, np.nan) - 1) * 100
    by_line = by_line.reset_index()

    fares = (o[o["period"] == "after"].groupby("fare")[["trips", "revenue"]].sum() / nd["after"]).reset_index()

    # headway cut: causal entry effect (DiD, notebook 03) x Yellow entries before the cut x Yellow-origin average fare
    yo = o[(o["period"] == "after") & o["origin"].isin(C.YELLOW_NEW)]
    fare_y = yo["revenue"].sum() / yo["trips"].sum()
    e = D.load_station_hourly("entries")
    e = e[e["station"].isin(C.YELLOW_NEW) & e["date"].str.startswith("2025-09") & (e["hour"] != 6)]
    e = e[[pd.Timestamp(x).dayofweek < 5 for x in e["date"]]]
    daily = e.groupby("date")["entries"].sum()
    base = daily[daily.index < "2025-09-10"].mean()
    extra_day = headway_effect * base * fare_y
    headway = {"yellow_weekday_entries_before_cut": base, "yellow_origin_avg_fare": fare_y, "did_entry_effect": headway_effect,
               "extra_revenue_per_weekday": extra_day, "extra_revenue_per_year_weekdays": extra_day * weekdays_per_year}
    return {"summary": summary, "yellow": pd.DataFrame([yellow]), "by_line": by_line, "fares": fares,
            "headway": pd.DataFrame([headway])}
