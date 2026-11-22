"""Extensions after the first round of results (notebook 10).

1. Pink Line pre-registration: bus-link scores from the 9 Nov 2026 GTFS (5 days before the
   14 Nov 2026 opening), top-10 list frozen and hashed before any Pink Line ridership exists.
2. Feeder network maturity: metro-feeder (MF) routes and the metro stations they serve, 2024-2026.
3. Heterogeneity: does the (null) diversion differ by origin type (job centre vs residential),
   by the origin's own bus access to the corridor, or by origin population?
4. Pair-level substitution: is the Yellow Line a real alternative for this origin-destination pair
   (RV Road no farther by metro than the current destination)?
5. Observational vs causal: cross-station association between bus supply and metro ridership
   (the kind of evidence in prior Bengaluru studies) set against the causal null.
6. Second shock: did bus-linked old stations lose entries after the 10 Sep 2025 headway cut?
7. Sensitivity: bus-link score rebuilt without trips that list only 1-2 stops.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import bus as B
from . import config as C
from . import data as D
from . import econ as E
from . import panels as P

# Pink Line (operational section, opened 14 Nov 2026). Coordinates: OpenStreetMap route relation
# "Pink Line (Kalena Agrahara - Suddaguntepalya)", stop positions with opening_date 2026-11-14.
PINK_OPEN = "2026-11-14"
PINK_SNAPSHOT = "2026-11-09"
PINK_INTERCHANGE = "Jayadeva Hospital"          # already a Yellow Line station
PINK_NEW = pd.DataFrame([
    ("Kalena Agrahara", 12.87195, 77.59383),
    ("Hulimavu", 12.88136, 77.59593),
    ("Bilekahalli IIM-B", 12.89538, 77.59953),
    ("N S Palya", 12.91027, 77.60010),
    ("Suddaguntepalya", 12.92986, 77.60053),
], columns=["station", "lat", "lon"])


# ----------------------------------------------------------------------------- 1. Pink Line
def pink_scores(router=None, catchment_m: float = C.CATCHMENT_M, corridor_m: float = C.CORRIDOR_M) -> pd.DataFrame:
    """Bus-link score of every existing station (all 83) to the new Pink corridor."""
    sc = B.station_scores(PINK_SNAPSHOT, catchment_m, corridor_m, router=router, corridor_points=PINK_NEW)
    sc = sc.rename(columns={"YellowLink": "PinkLink", "YellowLinkDir": "PinkLinkDir",
                            "YellowLinkTrips": "PinkLinkTrips"})
    od = D.load_od()
    hops = od[od["dest"] == PINK_INTERCHANGE].groupby("origin")["hops"].max()
    sc["MetroHopsToJayadeva"] = sc["station"].map(hops)
    sc.loc[sc["station"] == PINK_INTERCHANGE, "MetroHopsToJayadeva"] = 0
    return sc.drop(columns=["MetroHopsToRV"], errors="ignore")


def freeze_pink(scores: pd.DataFrame, k: int = C.TOP_K_TRANSFER) -> dict:
    """Freeze the top-k Pink bus-transfer stations with a hash. Uses no ridership at all."""
    p = C.paths()
    elig = scores[(scores["station"] != PINK_INTERCHANGE) & (~scores["near_corridor"]) & (scores["BusTrips"] > 0)]
    top = elig.sort_values(["PinkLink", "PinkLinkTrips"], ascending=False).head(k)
    rec = {
        "event": f"Pink Line opening {PINK_OPEN} (Kalena Agrahara - Suddaguntepalya, 5 new stations)",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rule": f"top {k} existing stations by PinkLink (GTFS snapshot {PINK_SNAPSHOT}, {C.CATCHMENT_M} m walk "
                f"catchment, {C.CORRIDOR_M} m straight-line corridor), excluding {PINK_INTERCHANGE} and stations "
                "whose catchment touches the corridor",
        "primary_test": "log(1+trips_odtb) ~ FE[o x date x band] + FE[o x d x band] + post x zPinkLink_d, "
                        "clustered by destination; same as the Yellow Line test",
        "stations": top["station"].tolist(),
    }
    rec["sha256"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
    (p["out"] / "frozen_pink_stations.json").write_text(json.dumps(rec, indent=2))
    md = ["# Pre-registration: Pink Line bus-diversion test", "",
          f"- Created (UTC): {rec['created_utc']}", f"- Event: {rec['event']}", f"- Rule: {rec['rule']}",
          f"- Primary test: {rec['primary_test']}", "- Frozen stations: " + ", ".join(rec["stations"]),
          f"- SHA-256: {rec['sha256']}", "",
          "No Pink Line ridership was available or examined when this list was frozen. The test runs once",
          "post-opening station-pair data (Nov-Dec 2026) is obtained by RTI."]
    (p["out"] / "preregistration_pink.md").write_text("\n".join(md))
    return rec


# ----------------------------------------------------------------------------- 2. feeders
def feeder_summary(snapshots: list[str], stations: pd.DataFrame | None = None, radius_m: float = 400) -> pd.DataFrame:
    """Metro-feeder (route short name starting 'MF') routes, trips and metro stations served."""
    stations = stations if stations is not None else D.metro_stations()
    allst = pd.concat([stations[["station", "lat", "lon"]], PINK_NEW], ignore_index=True)
    rows = []
    for s in snapshots:
        g = D.load_gtfs(s, ("stops", "routes", "trips", "stop_times", "calendar"))
        r = g["routes"]
        mf = r[r["route_short_name"].fillna("").str.upper().str.startswith("MF")]
        trips = D.weekday_trips(g)
        t = trips[trips["route_id"].isin(mf["route_id"])]
        st = g["stop_times"][g["stop_times"]["trip_id"].isin(t["trip_id"])]
        stops = g["stops"][g["stops"]["stop_id"].isin(st["stop_id"].unique())]
        served = set()
        for _, m in allst.iterrows():
            if (B.haversine(m["lat"], m["lon"], stops["stop_lat"].values, stops["stop_lon"].values) <= radius_m).any():
                served.add(m["station"])
        rows.append({"snapshot": s, "feeder_route_ids": len(mf), "feeder_services": mf["route_short_name"].nunique(),
                     "feeder_weekday_trips": len(t), "metro_stations_served": len(served)})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- 3-4. heterogeneity
def origin_characteristics(scores: pd.DataFrame, pop: pd.Series | None = None) -> pd.DataFrame:
    """Per old station: job-centre index, own bus access to the Yellow corridor, population."""
    pre_wk = [d for d in C.PRE_DAYS if pd.Timestamp(d).dayofweek < 5 and d not in C.EVENT_DAYS]
    sp = P.station_panel(pre_wk)
    am = sp[sp["hour"].between(7, 10)].groupby("station")[["entries", "exits"]].sum()
    out = pd.DataFrame({"job_index": np.log((am["exits"] + 1) / (am["entries"] + 1))})
    sc = scores.set_index("station")
    out["own_link"] = sc["YellowLink"].reindex(out.index)
    out["log_pop"] = np.log1p(pop.reindex(out.index)) if pop is not None else np.nan
    return out


def _z(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std()


def heterogeneity(panel: pd.DataFrame, chars: pd.DataFrame, FE: list[str]) -> pd.DataFrame:
    """post x zYellowLink_d interacted with standardised origin characteristics, one model each."""
    rows = []
    olds = panel["origin"].unique()
    for c, label in (("job_index", "origin is a job centre (AM exits / entries)"),
                     ("own_link", "origin's own bus link to the corridor"),
                     ("log_pop", "origin population within 800 m")):
        if chars[c].isna().all():
            continue
        z = _z(chars.loc[olds, c])
        panel[f"zo_{c}"] = panel["origin"].map(z)
        panel[f"het_{c}"] = panel["post_zYellowLink_d"] * panel[f"zo_{c}"]
        m = E.fit(panel, "ltrips", ["post_zYellowLink_d", f"het_{c}"], FE, "dest")
        rows.append(E.tidy(m, label))
    return pd.concat(rows, ignore_index=True)


def pair_substitution(panel: pd.DataFrame, FE: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pair-level exposure: Yellow is a natural substitute for o->d (+bus) when RV Road is no
    farther from o by metro than d is. Tests post x zYellowLink_d x substitute_od."""
    od = D.load_od()
    hops = od.groupby(["origin", "dest"])["hops"].max()
    to_rv = od[od["dest"] == C.INTERCHANGE].groupby("origin")["hops"].max()
    pairs = panel[["origin", "dest"]].drop_duplicates()
    pairs["hops_od"] = [hops.get((o, d), np.nan) for o, d in zip(pairs["origin"], pairs["dest"])]
    pairs["hops_o_rv"] = pairs["origin"].map(to_rv)
    pairs["extra_hops_via_rv"] = pairs["hops_o_rv"] - pairs["hops_od"]
    pairs["substitute"] = (pairs["extra_hops_via_rv"] <= 0).astype(int)
    x = panel.merge(pairs[["origin", "dest", "extra_hops_via_rv", "substitute"]], on=["origin", "dest"], how="left")
    x["post_zYL_x_sub"] = x["post_zYellowLink_d"] * x["substitute"]
    x["post_sub"] = x["post"] * x["substitute"]
    x["z_extra"] = _z(x["extra_hops_via_rv"].astype(float))
    x["post_zYL_x_extra"] = x["post_zYellowLink_d"] * x["z_extra"]
    res = [E.tidy(E.fit(x, "ltrips", ["post_zYellowLink_d", "post_zYL_x_sub", "post_sub"], FE, "dest"),
                  "binary: RV Road no farther than destination"),
           E.tidy(E.fit(x, "ltrips", ["post_zYellowLink_d", "post_zYL_x_extra"], FE, "dest"),
                  "continuous: extra metro stops via RV Road (z)")]
    summary = pairs.describe().T
    return pd.concat(res, ignore_index=True), summary


# ----------------------------------------------------------------------------- 5. observational
def observational_cross_section(scores: pd.DataFrame, pop: pd.Series | None = None) -> pd.DataFrame:
    """Before the opening, across old stations: log daily entries on log bus trips and controls."""
    import statsmodels.formula.api as smf
    pre_wk = [d for d in C.PRE_DAYS if pd.Timestamp(d).dayofweek < 5 and d not in C.EVENT_DAYS]
    sp = P.station_panel(pre_wk, kinds=("entries",))
    daily = sp.groupby("station")["entries"].sum() / len(pre_wk)
    sc = scores.set_index("station")
    df = pd.DataFrame({"lent": np.log(daily)})
    df["lbus"] = np.log1p(sc["BusTrips"].reindex(df.index))
    df["zlink"] = _z(sc["YellowLink"].reindex(df.index))
    df["hops"] = sc["MetroHopsToRV"].reindex(df.index)
    lines = sc["lines"].reindex(df.index).fillna("")
    df["purple"] = lines.str.contains("PURPLE").astype(int)
    df["lpop"] = np.log1p(pop.reindex(df.index)) if pop is not None else 0.0
    df = df[df.index.isin(P.old_stations())].dropna()
    rows = []
    for name, f in (("bus trips only", "lent ~ lbus"),
                    ("+ population, line, distance to RV Road", "lent ~ lbus + lpop + purple + hops"),
                    ("+ Yellow bus link", "lent ~ lbus + zlink + lpop + purple + hops")):
        m = smf.ols(f, data=df).fit(cov_type="HC1")
        for term in ("lbus", "zlink"):
            if term in m.params:
                rows.append({"model": name, "term": term, "estimate": m.params[term], "se": m.bse[term],
                             "p": m.pvalues[term], "r2": m.rsquared, "n": int(m.nobs)})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- 6. second shock
def headway_shock_on_old(scores: pd.DataFrame, transfer: list[str]) -> pd.DataFrame:
    """Old stations, 1-30 Sep 2025: did bus-linked stations lose entries/exits after 10 Sep?"""
    olds = [s for s in P.old_stations() if s != C.INTERCHANGE]
    sp = P.station_panel(C.SEP_DAYS, stations=olds)
    sp = sp[sp["hour"] != 6]                        # first train moved to 6:00 on 10 Sep
    sc = scores.set_index("station")
    z = _z(sc.loc[olds, "YellowLink"])
    sp["after"] = (sp["date"] >= "2025-09-10").astype(int)
    sp["after_zYL"] = sp["after"] * sp["station"].map(z)
    sp["after_transfer"] = sp["after"] * sp["station"].isin(transfer).astype(int)
    rows = []
    for k in ("lentries", "lexits"):
        rows.append(E.tidy(E.fit(sp, k, ["after_zYL"], ["fe_s_h", "fe_t_h"], "station"), f"{k} · per SD YellowLink"))
        rows.append(E.tidy(E.fit(sp, k, ["after_transfer"], ["fe_s_h", "fe_t_h"], "station"), f"{k} · transfer stations"))
    return pd.concat(rows, ignore_index=True)


# ----------------------------------------------------------------------------- 8. bus speeds
def scheduled_speeds(snapshot: str = C.SNAPSHOT_BEFORE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Scheduled bus operating speed (km/h) by hour of day, from GTFS stop times (cf. Nesmachnow
    et al. 2023 for Montevideo). Uses trips with 3+ stops; BMTC GTFS times are partly interpolated,
    so speeds describe the timetable, not observed traffic."""
    g = D.load_gtfs(snapshot, ("stops", "trips", "stop_times", "calendar"))
    z = __import__("zipfile").ZipFile(D.gtfs_path(snapshot))
    times = pd.read_csv(z.open("stop_times.txt"), usecols=["trip_id", "stop_sequence", "departure_time"], dtype=str)
    times["stop_sequence"] = times["stop_sequence"].astype(int)
    st = g["stop_times"].merge(times, on=["trip_id", "stop_sequence"])
    st = st[st["trip_id"].isin(D.weekday_trips(g)["trip_id"])]
    st = st[st.groupby("trip_id")["stop_id"].transform("size") >= 3]
    st = st.merge(g["stops"][["stop_id", "stop_lat", "stop_lon"]], on="stop_id").sort_values(["trip_id", "stop_sequence"])
    hms = st["departure_time"].str.split(":", expand=True).astype(float)
    st["t"] = hms[0] * 3600 + hms[1] * 60 + hms[2]
    first = st.groupby("trip_id").first()
    last = st.groupby("trip_id").last()
    seg = st.groupby("trip_id")[["stop_lat", "stop_lon"]].shift()
    st["seg_m"] = B.haversine(seg["stop_lat"].values, seg["stop_lon"].values, st["stop_lat"].values, st["stop_lon"].values)
    km = st.groupby("trip_id")["seg_m"].sum() / 1000
    hours = (last["t"] - first["t"]) / 3600
    trip = pd.DataFrame({"km": km, "hours": hours, "start_hour": (first["t"] // 3600) % 24}).query("hours > 0 and km > 1")
    trip["kmh"] = trip["km"] / trip["hours"]
    trip = trip[trip["kmh"].between(3, 80)]                     # drop impossible timetables
    by_hour = trip.groupby("start_hour").agg(trips=("kmh", "size"), median_kmh=("kmh", "median"),
                                             mean_kmh=("kmh", "mean")).reset_index()
    return trip, by_hour
