"""All-lines analysis (notebook 11): every Purple, Green and Yellow station, not just the Yellow Line.

A. Bus-metro integration index per station and under-served busy stations.
B. Line-by-line demand: hourly profiles, peak shares, interchange load, flows between lines.
C. How the Yellow Line opening changed ridership on each line (OD and station level).
D. New-station prediction with Spark MLlib: train on old stations, predict the 15 Yellow stations,
   with metro-only vs metro + hourly bus features vs shuffled-bus placebo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import bus as B
from . import config as C
from . import data as D
from . import panels as P

LINE_OF = {"PURPLE": "Purple", "GREEN": "Green", "YELLOW": "Yellow",
           "GREEN+PURPLE": "Interchange (Majestic)", "GREEN+YELLOW": "Interchange (RV Road)"}
MAJESTIC = "Nadaprabhu Kempegowda Station, Majestic"


def _weekdays(days):
    return [d for d in days if pd.Timestamp(d).dayofweek < 5 and d not in C.EVENT_DAYS]


# ----------------------------------------------------------------------------- bus by hour
def bus_station_hourly(snapshot: str, router, catchment_m: float = C.CATCHMENT_M) -> pd.DataFrame:
    """Weekday bus trips stopping within `catchment_m` walk of each station, by hour of day,
    plus metro-feeder (MF) trips. Trips listing 1-2 stops are dropped (feed artefacts)."""
    import zipfile
    g = D.load_gtfs(snapshot, ("stops", "routes", "trips", "stop_times", "calendar"))
    z = zipfile.ZipFile(D.gtfs_path(snapshot))
    tm = pd.read_csv(z.open("stop_times.txt"), usecols=["trip_id", "stop_sequence", "departure_time"], dtype=str)
    tm["stop_sequence"] = tm["stop_sequence"].astype(int)
    st = g["stop_times"].merge(tm, on=["trip_id", "stop_sequence"])
    trips = D.weekday_trips(g)[["trip_id", "route_id"]]
    st = st.merge(trips, on="trip_id")
    st = st[st.groupby("trip_id")["stop_id"].transform("size") >= 3]
    st["hour"] = st["departure_time"].str.split(":").str[0].astype(int) % 24
    mf = set(g["routes"].loc[g["routes"]["route_short_name"].fillna("").str.upper().str.startswith("MF"), "route_id"])
    st["feeder"] = st["route_id"].isin(mf)
    if router is not None:
        dist = router.distances(g["stops"])
        near = dist[dist["walk_m"] <= catchment_m][["station", "stop_id"]]
    else:   # straight line from the station centre: robust where the OSM walk graph misses crossings
        stn = D.metro_stations()
        parts = []
        for _, m in stn.iterrows():
            d = B.haversine(m["lat"], m["lon"], g["stops"]["stop_lat"].values, g["stops"]["stop_lon"].values)
            parts.append(pd.DataFrame({"station": m["station"], "stop_id": g["stops"]["stop_id"].values[d <= catchment_m]}))
        near = pd.concat(parts, ignore_index=True)
    x = st.merge(near, on="stop_id")
    hourly = (x.groupby(["station", "hour"])["trip_id"].nunique().unstack(fill_value=0)
              .reindex(columns=range(24), fill_value=0))
    tot = x.groupby("station").agg(bus_trips=("trip_id", "nunique"), bus_routes=("route_id", "nunique"))
    tot["feeder_trips"] = x[x["feeder"]].groupby("station")["trip_id"].nunique()
    return hourly, tot.fillna(0)


# ----------------------------------------------------------------------------- A. integration
def integration_index(scores: pd.DataFrame, bus_tot: pd.DataFrame, pop: pd.Series) -> pd.DataFrame:
    """Index = mean z-score of bus trips, bus routes, feeder trips (log) and walk-catchment
    population (log); compared with September weekday ridership to flag under-served stations."""
    st = D.metro_stations().set_index("station")
    e = D.load_station_hourly("entries")
    sep = e[e["date"].isin(_weekdays(C.SEP_DAYS))]
    daily = sep.groupby("station")["entries"].sum() / len(_weekdays(C.SEP_DAYS))
    df = pd.DataFrame(index=st.index)
    df["line"] = st["lines"].map(LINE_OF)
    df["bus_trips"] = bus_tot["bus_trips"].reindex(df.index).fillna(0)
    df["bus_routes"] = bus_tot["bus_routes"].reindex(df.index).fillna(0)
    df["feeder_trips"] = bus_tot["feeder_trips"].reindex(df.index).fillna(0)
    df["pop_800m"] = pop.reindex(df.index).fillna(0)
    df["sep_daily_entries"] = daily.reindex(df.index)
    z = lambda s: (s - s.mean()) / s.std()
    comps = [z(np.log1p(df[c])) for c in ("bus_trips", "bus_routes", "feeder_trips", "pop_800m")]
    df["integration_index"] = sum(comps) / len(comps)
    df["ridership_z"] = z(np.log1p(df["sep_daily_entries"]))
    df["gap"] = df["ridership_z"] - df["integration_index"]        # busy but poorly connected = high
    df["integration_rank"] = df["integration_index"].rank(ascending=False).astype(int)
    return df.sort_values("integration_index", ascending=False)


# ----------------------------------------------------------------------------- B. demand by line
def line_demand() -> dict:
    st = D.metro_stations().set_index("station")["lines"].map(LINE_OF)
    e = D.load_station_hourly("entries")
    e["line"] = e["station"].map(st)
    e["period"] = np.select([e["date"].isin(C.PRE_DAYS), e["date"].isin(C.POST_DAYS)], ["Aug 1-10", "Aug 11-18"], "September")
    wk = e[e["date"].isin(_weekdays(C.AUG_DAYS + C.SEP_DAYS))]
    ndays = wk.groupby("period")["date"].nunique()
    hourly = wk.groupby(["period", "line", "hour"])["entries"].sum().unstack("hour").div(ndays, level="period", axis=0)
    daily = wk.groupby(["period", "line"])["entries"].sum().div(ndays, level="period").unstack("period")
    peak = wk.assign(band=np.select([wk.hour.between(8, 10), wk.hour.between(17, 19)], ["am", "pm"], "other")) \
        .groupby(["line", "band"])["entries"].sum().unstack()
    peak = peak.div(peak.sum(axis=1), axis=0)
    od = D.load_od()
    od = od[od["origin"] != od["dest"]]
    od["lo"], od["ld"] = od["origin"].map(st), od["dest"].map(st)
    od["period"] = np.where(od["date"].isin(C.POST_DAYS), "after", "before")
    odw = od[od["date"].isin(_weekdays(C.AUG_DAYS))]
    nd = odw.groupby("period")["date"].nunique()
    flows = odw.groupby(["period", "lo", "ld"])["trips"].sum().div(nd, level="period").unstack("period").fillna(0)
    flows["change_pct"] = (flows["after"] / flows["before"].replace(0, np.nan) - 1) * 100
    return {"hourly": hourly, "daily": daily, "peak": peak, "flows": flows.sort_values("after", ascending=False)}


# ----------------------------------------------------------------------------- C. opening effect by line
def opening_effect_by_line(scores: pd.DataFrame, FE=("fe_o_t", "fe_o_d")) -> pd.DataFrame:
    """Main OD test run separately for destinations on each old line, and the change in trips
    leaving each line's stations (weekdays, before vs after)."""
    from . import econ as E
    st = D.metro_stations().set_index("station")["lines"].map(LINE_OF)
    panel = P.attach_exposure(P.od_panel(D.load_od(), by="band"), scores, "dest")
    rows = []
    for line in ("Purple", "Green", "Interchange (Majestic)"):
        sub = panel[panel["dest"].map(st) == line]
        if sub["dest"].nunique() < 3:
            continue
        m = E.fit(sub, "ltrips", ["post_zYellowLink_d"], list(FE), "dest")
        t = E.tidy(m, f"destinations on {line}")
        t["destinations"] = sub["dest"].nunique()
        rows.append(t)
    # origin-line totals
    od = D.load_od()
    od = od[od["date"].isin(_weekdays(C.AUG_DAYS)) & (od["origin"] != od["dest"])]
    od["lo"] = od["origin"].map(st)
    od["to_yellow"] = od["dest"].isin(C.YELLOW_NEW)
    od["period"] = np.where(od["date"].isin(C.POST_DAYS), "after", "before")
    nd = od.groupby("period")["date"].nunique()
    tot = od.groupby(["lo", "period"])["trips"].sum().unstack().div(nd)
    yel = od[od["to_yellow"]].groupby(["lo", "period"])["trips"].sum().unstack().reindex(tot.index).fillna(0).div(nd)
    out = pd.DataFrame({"trips_before": tot["before"], "trips_after": tot["after"],
                        "change_pct": (tot["after"] / tot["before"] - 1) * 100,
                        "to_yellow_after": yel["after"],
                        "share_to_yellow_after_pct": yel["after"] / tot["after"] * 100})
    return pd.concat(rows, ignore_index=True), out


# ----------------------------------------------------------------------------- D. new-station ML
def new_station_table(scores: pd.DataFrame, bus_hourly: pd.DataFrame, bus_tot: pd.DataFrame,
                      pop: pd.Series, seed: int = C.SEED) -> pd.DataFrame:
    """Station x hour rows (September weekdays, 6-22 h). Target: log(1 + mean entries).
    Old stations train; the 15 new Yellow stations test (they have no ridership history)."""
    st = D.metro_stations().set_index("station")
    e = D.load_station_hourly("entries")
    sep = e[e["date"].isin(_weekdays(C.SEP_DAYS))]
    y = sep.groupby(["station", "hour"])["entries"].mean().rename("entries").reset_index()
    y = y[y["hour"].between(7, 22)]
    od = D.load_od()
    hops_maj = od[od["dest"] == MAJESTIC].groupby("origin")["hops"].max()
    x = y.copy()
    x["label"] = np.log1p(x["entries"])
    x["lat"] = x["station"].map(st["lat"]); x["lon"] = x["station"].map(st["lon"])
    x["hops_to_majestic"] = x["station"].map(hops_maj).fillna(0)
    x["is_interchange"] = x["station"].map(st["lines"]).str.contains(r"\+").astype(int)
    x["log_pop_800m"] = np.log1p(x["station"].map(pop).fillna(0))
    x["log_bus_trips"] = np.log1p(x["station"].map(bus_tot["bus_trips"]).fillna(0))
    x["log_bus_routes"] = np.log1p(x["station"].map(bus_tot["bus_routes"]).fillna(0))
    x["log_feeder_trips"] = np.log1p(x["station"].map(bus_tot["feeder_trips"]).fillna(0))
    bh = bus_hourly.stack().rename("bh")
    x["log_bus_this_hour"] = np.log1p([bh.get((s, h), 0) for s, h in zip(x["station"], x["hour"])])
    # placebo: the same bus columns, but each station gets another station's bus data
    stations = x["station"].unique()
    perm = dict(zip(stations, np.random.default_rng(seed).permutation(stations)))
    src = x.set_index(["station", "hour"])
    for c in ("log_bus_trips", "log_bus_routes", "log_feeder_trips", "log_bus_this_hour"):
        x[f"placebo_{c}"] = [src[c].get((perm[s], h), 0.0) for s, h in zip(x["station"], x["hour"])]
    x["split"] = np.where(x["station"].isin(C.YELLOW_NEW), "new_yellow", "old")
    x.loc[x["station"] == C.INTERCHANGE, "split"] = "old"
    return x


METRO_X = ["lat", "lon", "hops_to_majestic", "is_interchange", "log_pop_800m"]
BUS_X = ["log_bus_trips", "log_bus_routes", "log_feeder_trips", "log_bus_this_hour"]


def new_station_ml(spark, table: pd.DataFrame, folds: int = 3, seed: int = C.SEED) -> pd.DataFrame:
    """Spark MLlib: LR, RF, GBT x feature sets; train on old stations, test on new Yellow stations.
    Reports RMSE/R2 on station-hours and MAPE on station daily totals (7-22 h)."""
    import os
    from pyspark.ml import Pipeline
    from pyspark.ml.evaluation import RegressionEvaluator
    from pyspark.ml.feature import OneHotEncoder, VectorAssembler
    from pyspark.ml.regression import GBTRegressor, LinearRegression, RandomForestRegressor
    from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
    sets = {"metro only": METRO_X, "metro + bus": METRO_X + BUS_X,
            "metro + shuffled bus": METRO_X + [f"placebo_{c}" for c in BUS_X]}
    C.paths()["cache"].mkdir(parents=True, exist_ok=True)
    f = C.paths()["cache"] / "new_station_table.parquet"
    table.to_parquet(f, index=False)
    sdf = spark.read.parquet(str(f) if os.name == "nt" else f"file://{f}").cache()
    train, test = sdf.where("split = 'old'"), sdf.where("split = 'new_yellow'")
    rows = []
    for set_name, feats in sets.items():
        oh = OneHotEncoder(inputCols=["hour"], outputCols=["hour_oh"], handleInvalid="keep")
        va = VectorAssembler(inputCols=["hour_oh"] + feats, outputCol="features")
        lr = LinearRegression(); rf = RandomForestRegressor(seed=seed); gbt = GBTRegressor(seed=seed)
        models = {"Linear Regression": (lr, ParamGridBuilder().addGrid(lr.regParam, [0.0, 0.1]).addGrid(lr.elasticNetParam, [0.0, 0.5]).build()),
                  "Random Forest": (rf, ParamGridBuilder().addGrid(rf.numTrees, [100]).addGrid(rf.maxDepth, [5, 8]).build()),
                  "GBT": (gbt, ParamGridBuilder().addGrid(gbt.maxIter, [50]).addGrid(gbt.maxDepth, [3, 5]).build())}
        for mname, (est, grid) in models.items():
            cv = CrossValidator(estimator=Pipeline(stages=[oh, va, est]), estimatorParamMaps=grid,
                                evaluator=RegressionEvaluator(metricName="rmse"), numFolds=folds, seed=seed, parallelism=4)
            best = cv.fit(train).bestModel
            pred = best.transform(test).select("station", "hour", "label", "entries", "prediction").toPandas()
            rmse = float(np.sqrt(((pred.label - pred.prediction) ** 2).mean()))
            r2 = 1 - ((pred.label - pred.prediction) ** 2).sum() / ((pred.label - pred.label.mean()) ** 2).sum()
            day = pred.assign(p=np.expm1(pred.prediction)).groupby("station")[["entries", "p"]].sum()
            mape = float((abs(day.p - day.entries) / day.entries).mean() * 100)
            rho = float(day["p"].rank().corr(day["entries"].rank()))
            rows.append({"features": set_name, "model": mname, "rmse_log": rmse, "r2_log": float(r2),
                         "daily_mape_pct": mape, "rank_corr": rho, "test_stations": day.shape[0]})
    return pd.DataFrame(rows)


def unseen_station_cv(spark, table: pd.DataFrame, k: int = 5, seed: int = C.SEED) -> pd.DataFrame:
    """Leave-stations-out cross-validation on the old (mature) stations: each fold hides ~14 whole
    stations, so the model cannot memorise a station's level and must predict it from its traits.
    This is the planning question for a station without ridership history."""
    import os
    from pyspark.ml import Pipeline
    from pyspark.ml.feature import OneHotEncoder, VectorAssembler
    from pyspark.ml.regression import GBTRegressor, LinearRegression, RandomForestRegressor
    old = table[table["split"] == "old"].copy()
    stations = np.array(sorted(old["station"].unique()))
    fold_of = dict(zip(np.random.default_rng(seed).permutation(stations), np.arange(len(stations)) % k))
    old["fold"] = old["station"].map(fold_of)
    f = C.paths()["cache"] / "unseen_cv_table.parquet"
    old.to_parquet(f, index=False)
    sdf = spark.read.parquet(str(f) if os.name == "nt" else f"file://{f}").cache()
    sets = {"metro only": METRO_X, "metro + bus": METRO_X + BUS_X,
            "metro + shuffled bus": METRO_X + [f"placebo_{c}" for c in BUS_X]}
    models = {"Linear Regression": lambda: LinearRegression(regParam=0.1, elasticNetParam=0.0),
              "Random Forest": lambda: RandomForestRegressor(numTrees=100, maxDepth=6, seed=seed),
              "GBT": lambda: GBTRegressor(maxIter=50, maxDepth=3, seed=seed)}
    preds = []
    for set_name, feats in sets.items():
        for mname, mk in models.items():
            for fo in range(k):
                pipe = Pipeline(stages=[OneHotEncoder(inputCols=["hour"], outputCols=["hour_oh"], handleInvalid="keep"),
                                        VectorAssembler(inputCols=["hour_oh"] + feats, outputCol="features"), mk()])
                m = pipe.fit(sdf.where(f"fold <> {fo}"))
                p = m.transform(sdf.where(f"fold = {fo}")).select("station", "hour", "label", "entries", "prediction").toPandas()
                p["features"], p["model"] = set_name, mname
                preds.append(p)
    P_ = pd.concat(preds, ignore_index=True)
    rows = []
    for (fs, mn), g in P_.groupby(["features", "model"]):
        rmse = float(np.sqrt(((g.label - g.prediction) ** 2).mean()))
        r2 = 1 - ((g.label - g.prediction) ** 2).sum() / ((g.label - g.label.mean()) ** 2).sum()
        day = g.assign(p=np.expm1(g.prediction)).groupby("station")[["entries", "p"]].sum()
        rows.append({"features": fs, "model": mn, "rmse_log": rmse, "r2_log": float(r2),
                     "daily_mape_pct": float((abs(day.p - day.entries) / day.entries).mean() * 100),
                     "rank_corr": float(day["p"].rank().corr(day["entries"].rank())), "stations": day.shape[0]})
    return pd.DataFrame(rows)
