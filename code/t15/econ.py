"""Estimators: fixed-effects OLS / PPML (pyfixest), event studies, randomisation
inference, wild-cluster bootstrap and a small synthetic-control routine."""
from __future__ import annotations

import numpy as np
import pandas as pd


# ----------------------------------------------------------------- pyfixest wrappers
def fit(df: pd.DataFrame, y: str, xs: list[str], fes: list[str], cluster: str | list[str],
        model: str = "ols"):
    import pyfixest as pf
    fml = f"{y} ~ {' + '.join(xs)} | {' + '.join(fes)}"
    vcov = {"CRV1": cluster if isinstance(cluster, str) else "+".join(cluster)}
    if model == "ols":
        return pf.feols(fml, data=df, vcov=vcov)
    if model == "ppml":
        return pf.fepois(fml, data=df, vcov=vcov)
    raise ValueError(model)


def tidy(m, label: str = "", keep: list[str] | None = None) -> pd.DataFrame:
    t = m.tidy().reset_index().rename(columns={"Coefficient": "term"})
    if keep:
        t = t[t["term"].isin(keep)]
    t.insert(0, "model", label)
    t["nobs"] = getattr(m, "_N", np.nan)
    return t


def event_study(df: pd.DataFrame, y: str, z: str, fes: list[str], cluster: str,
                time_col: str = "date", ref: str = "2025-08-07", model: str = "ols") -> pd.DataFrame:
    """beta_k for z x 1[time == k], k != ref."""
    d = df.copy()
    cols = []
    for k in sorted(d[time_col].unique()):
        if k == ref:
            continue
        c = f"es_{str(k).replace('-', '_')}"
        d[c] = d[z] * (d[time_col] == k)
        cols.append(c)
    m = fit(d, y, cols, fes, cluster, model)
    t = m.tidy().reset_index().rename(columns={"Coefficient": "term"})
    t[time_col] = t["term"].str.replace("es_", "").str.replace("_", "-")
    ref_row = {"term": "ref", time_col: ref, "Estimate": 0.0, "Std. Error": 0.0, "2.5%": 0.0, "97.5%": 0.0}
    return pd.concat([t, pd.DataFrame([ref_row])], ignore_index=True).sort_values(time_col)


# ----------------------------------------------------------------- FWL tools
def demean(df: pd.DataFrame, cols: list[str], fes: list[str], tol: float = 1e-9, maxit: int = 2000) -> np.ndarray:
    """Alternating projections: remove all fixed effects from each column."""
    X = df[cols].to_numpy(dtype=float).copy()
    codes = [pd.factorize(df[f])[0] for f in fes]
    counts = [np.bincount(c) for c in codes]
    for _ in range(maxit):
        delta = 0.0
        for c, n in zip(codes, counts):
            for j in range(X.shape[1]):
                means = np.bincount(c, weights=X[:, j]) / n
                X[:, j] -= means[c]
                delta = max(delta, np.abs(means).max())
        if delta < tol:
            break
    return X


def _crv1_t(x: np.ndarray, y: np.ndarray, g: np.ndarray) -> tuple[float, float]:
    xx = x @ x
    b = (x @ y) / xx
    u = y - b * x
    G = g.max() + 1
    s = np.bincount(g, weights=x * u, minlength=G)
    n, k = len(y), 1
    adj = G / (G - 1) * (n - 1) / (n - k)
    se = np.sqrt(adj * (s @ s)) / xx
    return b, b / se


def randomization_inference(df: pd.DataFrame, y: str, station_col: str, z_by_station: pd.Series,
                            fes: list[str], n_perm: int = 1000, seed: int = 15,
                            post_col: str = "post") -> dict:
    """Shuffle the station-level exposure across stations n_perm times.
    Statistic: FE-OLS coefficient on post x z (FWL)."""
    rng = np.random.default_rng(seed)
    yt = demean(df, [y], fes)[:, 0]
    stations = z_by_station.index.to_numpy()
    zvals = z_by_station.to_numpy(dtype=float)
    zvals = (zvals - zvals.mean()) / zvals.std()

    def beta_for(z):
        m = dict(zip(stations, z))
        x = df[post_col].to_numpy() * df[station_col].map(m).to_numpy(dtype=float)
        xt = demean(df.assign(_x=x), ["_x"], fes)[:, 0]
        return (xt @ yt) / (xt @ xt)

    b0 = beta_for(zvals)
    dist = np.array([beta_for(rng.permutation(zvals)) for _ in range(n_perm)])
    p = (1 + np.sum(np.abs(dist) >= abs(b0))) / (n_perm + 1)
    return {"beta": b0, "p_value": p, "dist": dist}


def wild_cluster_bootstrap(df: pd.DataFrame, y: str, x: str, fes: list[str], cluster: str,
                           reps: int = 9999, seed: int = 15, weights: str = "webb") -> dict:
    """Restricted (null-imposed) wild-cluster bootstrap-t for one regressor after
    partialling out the fixed effects. Webb 6-point weights suit few clusters."""
    rng = np.random.default_rng(seed)
    Z = demean(df, [y, x], fes)
    yt, xt = Z[:, 0], Z[:, 1]
    g = pd.factorize(df[cluster])[0]
    G = g.max() + 1
    b, t0 = _crv1_t(xt, yt, g)
    u0 = yt                      # residuals under H0: beta = 0
    if weights == "webb":
        pts = np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)])
    else:
        pts = np.array([-1.0, 1.0])
    tstar = np.empty(reps)
    for r in range(reps):
        w = rng.choice(pts, size=G)[g]
        tstar[r] = _crv1_t(xt, u0 * w, g)[1]
    p = np.mean(np.abs(tstar) >= abs(t0))
    return {"beta": b, "t": t0, "p_value": p, "clusters": G, "reps": reps}


# ----------------------------------------------------------------- synthetic control
def synthetic_control(treated: pd.Series, donors: pd.DataFrame, pre_index) -> dict:
    """Non-negative weights summing to 1 that best match the treated series before the
    intervention. treated: index = time; donors: index = time, columns = donor units."""
    from scipy.optimize import minimize
    Y1 = treated.loc[pre_index].to_numpy(float)
    Y0 = donors.loc[pre_index].to_numpy(float)
    k = Y0.shape[1]
    obj = lambda w: np.sum((Y1 - Y0 @ w) ** 2)
    res = minimize(obj, np.full(k, 1 / k), method="SLSQP", bounds=[(0, 1)] * k,
                   constraints=({"type": "eq", "fun": lambda w: w.sum() - 1},),
                   options={"maxiter": 500})
    w = pd.Series(res.x, index=donors.columns)
    synth = donors @ w
    gap = treated - synth
    pre_rmspe = np.sqrt(np.mean(gap.loc[pre_index] ** 2))
    return {"weights": w.sort_values(ascending=False), "synthetic": synth, "gap": gap, "pre_rmspe": pre_rmspe}
