"""Next-day metro demand forecaster (notebook 11): a model built from our data for a real use.

For every station and hour of tomorrow, forecast metro entries with a calibrated 90% range and a
crowding warning, scored against the simple guesses an operator would otherwise use.

* Data: September 2025 station-hourly entries (30 continuous days, 83 stations).
* Learn on 8-17 Sep, calibrate ranges on 18-21 Sep, test once on 22-30 Sep (days never seen).
* Baselines: "same hour yesterday" and "same hour, same weekday last week".
* Models: Spark MLlib GBT and Random Forest on log entries.
* Ablation: what each group of inputs adds (lags, calendar, station traits, bus network),
  with 95% ranges from 1,000 bootstrap resamples of test days.
* Clustering: stations grouped by weekday hourly rhythm (MLlib KMeans, silhouette).
* Anomalies: test hours far outside the forecast range.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from . import config as C
from . import data as D

HOURS = range(6, 23)
HOLIDAYS = {"2025-09-05"}                     # Eid-e-Milad (Karnataka public holiday)
LEARN = (8, 17); CALIB = (18, 21); TEST = (22, 30)


def load_weather() -> pd.DataFrame:
    """Hourly Bengaluru rain (mm) and temperature (C), Aug-Sep 2025, from the Open-Meteo archive
    (downloaded once into data_raw/weather/). Used as observed, i.e. assuming a good next-day weather forecast."""
    import glob
    f = D.raw_dir() / "weather" / "bengaluru_hourly_weather_2025-08-09.csv"
    hits = [f] if f.exists() else [__import__("pathlib").Path(x) for x in
                                   glob.glob("/kaggle/input/**/weather/bengaluru_hourly_weather_2025-08-09.csv", recursive=True)]
    if hits:
        w = pd.read_csv(hits[0])
    else:
        import json, urllib.request
        url = ("https://archive-api.open-meteo.com/v1/archive?latitude=12.97&longitude=77.59&start_date=2025-08-01"
               "&end_date=2025-09-30&hourly=precipitation,temperature_2m&timezone=Asia%2FKolkata")
        req = urllib.request.Request(url, headers={"User-Agent": "t15-research-client"})
        w = pd.DataFrame(json.load(urllib.request.urlopen(req, timeout=60))["hourly"])
        f.parent.mkdir(parents=True, exist_ok=True); w.to_csv(f, index=False)
    w["date"] = w["time"].str[:10]; w["hour"] = w["time"].str[11:13].astype(int)
    w = w.sort_values("time")
    w["rain_3h"] = w["precipitation"].rolling(3, min_periods=1).sum()
    w["rain_day"] = w.groupby("date")["precipitation"].transform("sum")
    return w.rename(columns={"precipitation": "rain_mm", "temperature_2m": "temp_c"})[
        ["date", "hour", "rain_mm", "rain_3h", "rain_day", "temp_c"]]


def build_table(bus_tot: pd.DataFrame | None = None, pop: pd.Series | None = None, weather: bool = True) -> pd.DataFrame:
    e = D.load_station_hourly("entries")
    e = e[e["date"].str.startswith("2025-09") & e["hour"].isin(HOURS)].copy()
    full = pd.MultiIndex.from_product([sorted(e.station.unique()), sorted(e.date.unique()), list(HOURS)],
                                      names=["station", "date", "hour"]).to_frame(index=False)
    x = full.merge(e, on=["station", "date", "hour"], how="left").fillna({"entries": 0})
    x["day"] = x["date"].str[-2:].astype(int)
    x["dow"] = pd.to_datetime(x["date"]).dt.dayofweek
    x["weekend"] = (x["dow"] >= 5).astype(int)
    x["holiday"] = x["date"].isin(HOLIDAYS).astype(int)
    x["y"] = np.log1p(x["entries"])
    piv = x.pivot_table(index=["station", "hour"], columns="day", values="y")
    def lag(k):
        return [piv.at[(s, h), d - k] if d - k in piv.columns else np.nan for s, h, d in zip(x.station, x.hour, x.day)]
    x["lag1"] = lag(1); x["lag7"] = lag(7)
    x["mean7"] = np.nanmean(np.column_stack([lag(k) for k in range(1, 8)]), axis=1)
    daily = x.groupby(["station", "day"])["entries"].sum()
    x["yday_total"] = np.log1p([daily.get((s, d - 1), np.nan) for s, d in zip(x.station, x.day)])
    st = D.metro_stations().set_index("station")
    x["lat"] = x.station.map(st.lat); x["lon"] = x.station.map(st.lon)
    x["new_yellow"] = x.station.isin(C.YELLOW_NEW).astype(int)
    if bus_tot is not None:
        for c in ("bus_trips", "bus_routes", "feeder_trips"):
            x[f"log_{c}"] = np.log1p(x.station.map(bus_tot[c]).fillna(0))
    if pop is not None:
        x["log_pop"] = np.log1p(x.station.map(pop).fillna(0))
    if weather:
        x = x.merge(load_weather(), on=["date", "hour"], how="left")
    x["split"] = np.select([x.day.between(*LEARN), x.day.between(*CALIB), x.day.between(*TEST)],
                           ["learn", "calib", "test"], "warmup")
    return x[x.split != "warmup"].reset_index(drop=True)


GROUPS = {"lags": ["lag1", "lag7", "mean7", "yday_total"],
          "calendar": ["dow_f", "weekend", "holiday"],
          "station": ["lat", "lon", "new_yellow", "log_pop"],
          "bus": ["log_bus_trips", "log_bus_routes", "log_feeder_trips"],
          "weather": ["rain_mm", "rain_3h", "rain_day", "temp_c"]}


def _metrics(y, p):
    a, b = np.expm1(y), np.expm1(p)
    return {"mae": float(np.mean(np.abs(a - b))), "rmse": float(np.sqrt(np.mean((a - b) ** 2))),
            "mae_log": float(np.mean(np.abs(y - p)))}


def fit_predict(spark, tab: pd.DataFrame, feats: list[str], model: str = "gbt", seed: int = C.SEED,
                target: str = "level") -> pd.DataFrame:
    """target='level' learns log entries; target='delta' learns the change from the same hour last
    week (log scale) and adds it back, so the model refines the strongest simple guess."""
    from pyspark.ml import Pipeline
    from pyspark.ml.feature import OneHotEncoder, VectorAssembler
    from pyspark.ml.regression import GBTRegressor, RandomForestRegressor
    C.paths()["cache"].mkdir(parents=True, exist_ok=True)
    f = C.paths()["cache"] / "forecast_table.parquet"
    t = tab.copy(); t["dow_f"] = t["dow"]
    t["label"] = t["y"] - t["lag7"] if target == "delta" else t["y"]
    t.to_parquet(f, index=False)
    sdf = spark.read.parquet(str(f) if os.name == "nt" else f"file://{f}")
    inputs = ["hour_oh"] + [c for c in feats if c != "dow_f"] + (["dow_oh"] if "dow_f" in feats else [])
    enc = OneHotEncoder(inputCols=["hour", "dow"], outputCols=["hour_oh", "dow_oh"], handleInvalid="keep")
    reg = (GBTRegressor(labelCol="label", maxIter=80, maxDepth=5, stepSize=0.1, seed=seed) if model == "gbt"
           else RandomForestRegressor(labelCol="label", numTrees=150, maxDepth=10, seed=seed))
    pipe = Pipeline(stages=[enc, VectorAssembler(inputCols=inputs, outputCol="features", handleInvalid="keep"), reg])
    m = pipe.fit(sdf.where("split = 'learn'"))
    out = m.transform(sdf.where("split <> 'learn'")).select("station", "date", "day", "hour", "y", "entries", "split", "lag7", "prediction").toPandas()
    if target == "delta":
        out["prediction"] = out["prediction"] + out["lag7"]
    return out.drop(columns="lag7")


def evaluate(spark, tab: pd.DataFrame, n_boot: int = 1000, seed: int = C.SEED) -> dict:
    rng = np.random.default_rng(seed)
    test = tab[tab.split == "test"]
    base = {"same hour yesterday": test["lag1"].values, "same hour last week": test["lag7"].values}
    allf = [c for g, cols in GROUPS.items() if g != "weather" for c in cols]       # V1/V2 inputs
    wx = GROUPS["weather"] if "rain_mm" in tab.columns else []
    # V1 = learn the level (final: V1 Random Forest); V2 = learn the change from last week (tested, worse)
    runs = {"V1 GBT, level": ("gbt", allf, "level"), "V1 Random Forest, level": ("rf", allf, "level"),
            "V2 GBT, change vs last week": ("gbt", allf, "delta"), "V2 Random Forest, change vs last week": ("rf", allf, "delta"),
            "V1 RF without bus network": ("rf", [c for c in allf if c not in GROUPS["bus"]], "level"),
            "V1 RF without station traits": ("rf", [c for c in allf if c not in GROUPS["station"]], "level"),
            "V1 RF without calendar": ("rf", [c for c in allf if c not in GROUPS["calendar"]], "level")}
    if wx:   # V3: V1 + weather (rain this hour, last 3 hours, whole day; temperature)
        runs.update({"V3 Random Forest + weather": ("rf", allf + wx, "level"),
                     "V3 GBT + weather": ("gbt", allf + wx, "level")})
    preds = {k: fit_predict(spark, tab, f, m, target=t) for k, (m, f, t) in runs.items()}
    key = test[["station", "day", "hour"]].reset_index(drop=True)
    P = {k: key.merge(v, on=["station", "day", "hour"])["prediction"].values for k, v in preds.items()}
    P.update(base)
    y = test["y"].values
    days = test["day"].values
    ok = ~np.isnan(P["same hour last week"])
    rows = []
    for k, p in P.items():
        rows.append({"method": k, **_metrics(y[ok], p[ok])})
    res = pd.DataFrame(rows)
    best_naive = res[res.method.str.startswith("same")].sort_values("mae").iloc[0]
    res["skill_vs_best_simple_pct"] = (1 - res["mae"] / best_naive["mae"]) * 100
    # bootstrap of test days for the skill of the main model and the value of each input group
    ud = np.unique(days)
    abs_err = {k: np.abs(np.expm1(y) - np.expm1(p)) for k, p in P.items()}
    def boot(stat):
        out = []
        for _ in range(n_boot):
            pick = rng.choice(ud, len(ud), replace=True)
            idx = np.concatenate([np.where((days == d) & ok)[0] for d in pick])
            out.append(stat(idx))
        return np.percentile(out, [2.5, 97.5])
    nb = best_naive["method"]
    ci = []
    for k in P:
        lo, hi = boot(lambda i, k=k: (1 - abs_err[k][i].mean() / abs_err[nb][i].mean()) * 100)
        ci.append((k, lo, hi))
    res = res.merge(pd.DataFrame(ci, columns=["method", "skill_ci_low", "skill_ci_high"]), on="method")
    abl = []
    groups = [("bus network", "V1 RF without bus network", "V1 Random Forest, level"),
              ("station traits", "V1 RF without station traits", "V1 Random Forest, level"),
              ("calendar", "V1 RF without calendar", "V1 Random Forest, level")]
    if wx:   # weather is measured the other way round: V3 (with) against V1 (without)
        groups.append(("weather", "V1 Random Forest, level", "V3 Random Forest + weather"))
    for grp, k, main in groups:
        val = (abs_err[k][ok].mean() - abs_err[main][ok].mean()) / abs_err[nb][ok].mean() * 100
        lo, hi = boot(lambda i, k=k: (abs_err[k][i].mean() - abs_err[main][i].mean()) / abs_err[nb][i].mean() * 100)
        abl.append({"input group": grp, "skill points added": val, "ci_low": lo, "ci_high": hi,
                    "reliable": bool(lo > 0)})
    return {"results": res, "ablation": pd.DataFrame(abl), "preds": preds, "test": test}


def intervals_and_warnings(preds: pd.DataFrame, tab: pd.DataFrame, level: float = 0.90, crowd_q: float = 0.95) -> dict:
    """Split-conformal 90% ranges from calibration days (per station busyness tercile), crowding
    warnings for station-hours above the learning-period 95th percentile, and anomalies."""
    cal = preds[preds.split == "calib"].copy(); tst = preds[preds.split == "test"].copy()
    lvl = tab[tab.split == "learn"].groupby("station")["entries"].mean()
    terc = pd.qcut(lvl, 3, labels=["quiet", "medium", "busy"])
    for d in (cal, tst):
        d["group"] = d.station.map(terc)
        d["res"] = d["y"] - d["prediction"]
    q = cal.groupby("group", observed=True)["res"].apply(lambda r: np.quantile(np.abs(r), level))
    tst["lo"] = np.expm1(tst.prediction - tst.group.map(q).astype(float)).clip(lower=0)
    tst["hi"] = np.expm1(tst.prediction + tst.group.map(q).astype(float))
    tst["pred"] = np.expm1(tst.prediction)
    tst["inside"] = (tst.entries >= tst.lo) & (tst.entries <= tst.hi)
    cover = tst.groupby("group", observed=True)["inside"].mean().rename("coverage").reset_index()
    cover.loc[len(cover)] = ["all", tst.inside.mean()]
    thr = float(np.quantile(tab.loc[tab.split == "learn", "entries"], crowd_q))
    tt = tab[tab.split == "test"].set_index(["station", "day", "hour"])
    keys = list(zip(tst.station, tst.day, tst.hour))
    tst["naive_yday"] = np.expm1(tt["lag1"].reindex(keys).values)
    tst["naive_week"] = np.expm1(tt["lag7"].reindex(keys).values)
    actual = tst.entries > thr
    rows = []
    for name, warn in (("forecast model", tst.pred > thr), ("same hour last week", tst.naive_week > thr),
                       ("same hour yesterday", tst.naive_yday > thr)):
        tp = int((warn & actual).sum()); fp = int((warn & ~actual).sum()); fn = int((~warn & actual).sum())
        prec = tp / max(tp + fp, 1); rec = tp / max(tp + fn, 1)
        rows.append({"method": name, "threshold_entries_per_hour": round(thr), "crowded_hours": int(actual.sum()),
                     "warnings": tp + fp, "precision": prec, "recall": rec, "f1": 2 * prec * rec / max(prec + rec, 1e-9)})
    tst["z"] = tst["res"] / tst.group.map(q).astype(float)
    anomalies = tst.loc[tst["z"].abs() > 1.5, ["station", "date", "hour", "entries", "pred", "lo", "hi", "z"]] \
        .sort_values("z", key=np.abs, ascending=False)
    return {"coverage": cover, "warnings": pd.DataFrame(rows), "anomalies": anomalies, "test_preds": tst,
            "q": q.reset_index().rename(columns={"res": "log_halfwidth"})}


def cluster_stations(spark, k_range=range(2, 9), seed: int = C.SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Group stations by their weekday hourly rhythm (share of daily entries per hour), MLlib KMeans."""
    from pyspark.ml.clustering import KMeans
    from pyspark.ml.evaluation import ClusteringEvaluator
    from pyspark.ml.linalg import Vectors
    e = D.load_station_hourly("entries")
    wd = e[e.date.str.startswith("2025-09") & (pd.to_datetime(e.date).dt.dayofweek < 5)]
    prof = wd.groupby(["station", "hour"]).entries.sum().unstack(fill_value=0).reindex(columns=range(24), fill_value=0)
    prof = prof.div(prof.sum(axis=1), axis=0)
    sdf = spark.createDataFrame([(s, Vectors.dense(v)) for s, v in zip(prof.index, prof.values)], ["station", "features"])
    ev = ClusteringEvaluator()
    sil = []
    for k in k_range:
        m = KMeans(k=k, seed=seed).fit(sdf)
        sil.append({"k": k, "silhouette": ev.evaluate(m.transform(sdf))})
    sil = pd.DataFrame(sil)
    kbest = int(sil.sort_values("silhouette", ascending=False).iloc[0].k)
    m = KMeans(k=kbest, seed=seed).fit(sdf)
    lab = m.transform(sdf).select("station", "prediction").toPandas().set_index("station")["prediction"]
    out = prof.copy(); out["cluster"] = lab
    am = out[list(range(7, 11))].sum(axis=1); pm = out[list(range(17, 21))].sum(axis=1)
    out["am_share"] = am; out["pm_share"] = pm
    names = {}
    for c, g in out.groupby("cluster"):
        a, p = g.am_share.mean(), g.pm_share.mean()
        names[c] = "morning origin (residential)" if a > p + 0.05 else "evening origin (job centre)" if p > a + 0.05 else "balanced / all-day"
    out["cluster_name"] = out.cluster.map(names)
    return out.reset_index(), sil
