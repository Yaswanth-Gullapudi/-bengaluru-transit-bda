"""Spark MLlib comparison: do bus-network features improve prediction of metro ridership
after the Yellow Line opened?  3 models x 3 feature sets (metro only, + bus, + shuffled-bus placebo) x 2 targets."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from . import config as C
from . import data as D
from . import panels as P

METRO_FEATURES = ["hour", "dow", "weekend", "holiday", "pre_same_hour", "pre_daily",
                  "MetroHopsToRV", "is_purple", "is_green", "lat", "lon", "pop_800m"]
BUS_FEATURES = ["BusTrips", "BusRoutes", "BusStops", "YellowLink", "YellowLinkDir",
                "YellowLinkTrips", "Collinear"]


def feature_table(scores: pd.DataFrame, pop: pd.Series | None = None) -> pd.DataFrame:
    """Station-hour rows for OLD stations on post-opening days (Aug 11-18, Sep 1-30).

    pre_same_hour: mean entries at that station and hour on comparable pre-opening days
    (weekday vs weekend matched, event days excluded). Targets:
      y_level  = log1p(entries)
      y_change = log1p(entries) - log1p(pre_same_hour)   (redistribution)
    """
    ent = D.load_station_hourly("entries")
    olds = P.old_stations()
    ent = ent[ent["station"].isin(olds)].copy()
    ent["dow"] = pd.to_datetime(ent["date"]).dt.dayofweek
    ent["weekend"] = (ent["dow"] >= 5).astype(int)
    pre = ent[ent["date"].isin(C.PRE_DAYS) & ~ent["date"].isin(list(C.EVENT_DAYS)) & (ent["date"] != "2025-08-10")]
    pre_h = pre.groupby(["station", "weekend", "hour"])["entries"].mean().rename("pre_same_hour")
    pre_d = pre.groupby(["station", "date"])["entries"].sum().groupby("station").mean().rename("pre_daily")
    post = ent[ent["date"].isin(C.POST_DAYS + C.SEP_DAYS)].copy()
    post = post.join(pre_h, on=["station", "weekend", "hour"]).join(pre_d, on="station")
    post = post[post["pre_same_hour"].notna() & (post["hour"] >= 5) & (post["hour"] <= 23)]
    post["holiday"] = post["date"].isin(list(C.EVENT_DAYS)).astype(int)
    sc = scores.set_index("station")
    for c in BUS_FEATURES + ["MetroHopsToRV", "lat", "lon"]:
        post[c] = post["station"].map(sc[c]).astype(float)
    # placebo: the same bus features shuffled across stations (keeps the distribution,
    # breaks the link to the real bus network). Bus features must beat this, not just metro-only.
    rng = np.random.default_rng(C.SEED)
    st_list = np.array(sorted(post["station"].unique()))
    perm = dict(zip(st_list, rng.permutation(st_list)))
    for c in BUS_FEATURES:
        post[f"placebo_{c}"] = post["station"].map(perm).map(sc[c]).astype(float)
    post["is_purple"] = post["station"].map(sc["lines"]).str.contains("PURPLE").astype(int)
    post["is_green"] = post["station"].map(sc["lines"]).str.contains("GREEN").astype(int)
    post["pop_800m"] = post["station"].map(pop).astype(float) if pop is not None else 0.0
    post["y_level"] = np.log1p(post["entries"])
    post["y_change"] = post["y_level"] - np.log1p(post["pre_same_hour"])
    # train = all 8 post-opening days in August (weekdays + weekend); test = September
    post["split"] = np.where(post["date"].isin(C.POST_DAYS), "train", "test_sep")
    # first train moved to 6:00 on 10 Sep: drop hour 6 in September
    post = post[~((post["split"] == "test_sep") & (post["hour"] == 6))]
    return post.reset_index(drop=True)


def _models(seed: int = C.SEED, grid: str = "full"):
    from pyspark.ml.regression import GBTRegressor, LinearRegression, RandomForestRegressor
    from pyspark.ml.tuning import ParamGridBuilder
    lr = LinearRegression(featuresCol="features", labelCol="label")
    rf = RandomForestRegressor(featuresCol="features", labelCol="label", seed=seed)
    gbt = GBTRegressor(featuresCol="features", labelCol="label", seed=seed)
    if grid == "fast":   # smaller grid: same three models, fewer trees/iterations
        return {
            "LinearRegression": (lr, ParamGridBuilder().addGrid(lr.regParam, [0.0, 0.01, 0.1])
                                 .addGrid(lr.elasticNetParam, [0.0, 0.5]).build()),
            "RandomForest": (rf, ParamGridBuilder().addGrid(rf.numTrees, [100])
                             .addGrid(rf.maxDepth, [8, 12]).build()),
            "GBT": (gbt, ParamGridBuilder().addGrid(gbt.maxIter, [60])
                    .addGrid(gbt.maxDepth, [4, 6]).addGrid(gbt.stepSize, [0.1]).build()),
        }
    return {
        "LinearRegression": (lr, ParamGridBuilder().addGrid(lr.regParam, [0.0, 0.01, 0.1])
                             .addGrid(lr.elasticNetParam, [0.0, 0.5]).build()),
        "RandomForest": (rf, ParamGridBuilder().addGrid(rf.numTrees, [100, 300])
                         .addGrid(rf.maxDepth, [8, 12]).build()),
        "GBT": (gbt, ParamGridBuilder().addGrid(gbt.maxIter, [100, 200])
                .addGrid(gbt.maxDepth, [4, 6]).addGrid(gbt.stepSize, [0.05, 0.1]).build()),
    }


def run_comparison(spark, table: pd.DataFrame, targets=("y_level", "y_change"),
                   folds: int = 3, seed: int = C.SEED, grid: str = "full",
                   parallelism: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit every model x feature set x target with k-fold CV on 11-18 Aug;
    evaluate out of time on 1-30 Sep. Returns (metrics, importances)."""
    from pyspark.ml import Pipeline
    from pyspark.ml.evaluation import RegressionEvaluator
    from pyspark.ml.feature import OneHotEncoder, VectorAssembler
    from pyspark.ml.tuning import CrossValidator
    from pyspark.sql import functions as F

    placebo = [f"placebo_{c}" for c in BUS_FEATURES]
    sets = {"metro_only": METRO_FEATURES, "metro_plus_bus": METRO_FEATURES + BUS_FEATURES,
            "metro_plus_placebo": METRO_FEATURES + placebo}
    cols = sorted(set(METRO_FEATURES + BUS_FEATURES + placebo)) + list(targets) + ["split", "station", "date", "entries"]
    # stage through Parquet so tasks read from disk instead of carrying the data in every task
    import os
    C.paths()["cache"].mkdir(parents=True, exist_ok=True)
    stage_dir = str(C.paths()["cache"] / "ml_table.parquet")
    table[cols].to_parquet(stage_dir, index=False)
    sdf = spark.read.parquet(stage_dir if os.name == "nt" else "file://" + stage_dir).cache()
    sdf.count()
    metrics, imps = [], []
    for target in targets:
        base = sdf.withColumn("label", F.col(target))
        for set_name, feats in sets.items():
            ohe = OneHotEncoder(inputCols=["hour", "dow"], outputCols=["hour_oh", "dow_oh"], dropLast=True,
                                handleInvalid="keep")
            num = [f for f in feats if f not in ("hour", "dow")]
            va = VectorAssembler(inputCols=["hour_oh", "dow_oh"] + num, outputCol="features")
            for mname, (est, pgrid) in _models(seed, grid).items():
                pipe = Pipeline(stages=[ohe, va, est])
                grid_p = pgrid  # params refer to the estimator stage
                cv = CrossValidator(estimator=pipe, estimatorParamMaps=grid_p, numFolds=folds,
                                    evaluator=RegressionEvaluator(metricName="rmse"), seed=seed, parallelism=parallelism)
                t0 = time.time()
                model = cv.fit(base.where(F.col("split") == "train"))
                secs = time.time() - t0
                best = model.bestModel
                for split in ("train", "test_sep"):
                    pred = best.transform(base.where(F.col("split") == split))
                    row = {"target": target, "features": set_name, "model": mname, "split": split,
                           "fit_seconds": round(secs, 1)}
                    for metric in ("rmse", "mae", "r2"):
                        row[metric] = RegressionEvaluator(metricName=metric).evaluate(pred)
                    if target == "y_level":   # also on the passenger-count scale
                        pc = pred.select((F.exp("prediction") - 1).alias("p"), F.col("entries").alias("e"))
                        r = pc.select(F.sqrt(F.avg((F.col("p") - F.col("e")) ** 2)).alias("rmse"),
                                      F.avg(F.abs(F.col("p") - F.col("e"))).alias("mae")).first()
                        row["rmse_count"], row["mae_count"] = r["rmse"], r["mae"]
                    metrics.append(row)
                stage = best.stages[-1]
                cs = best.stages[0].categorySizes   # dropLast + handleInvalid=keep -> cs slots each
                names = [f"hour_{i}" for i in range(cs[0])] + [f"dow_{i}" for i in range(cs[1])] + num
                vals = (stage.featureImportances.toArray() if hasattr(stage, "featureImportances")
                        else np.abs(stage.coefficients.toArray()))
                imps.append(pd.DataFrame({"target": target, "features": set_name, "model": mname,
                                          "feature": names[:len(vals)], "importance": vals}))
                print(f"{target:9s} {set_name:15s} {mname:17s} done in {secs:.0f}s", flush=True)
    return pd.DataFrame(metrics), pd.concat(imps, ignore_index=True)
