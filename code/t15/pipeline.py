"""Shared building blocks so each notebook can reuse earlier results.

Results are looked up first in this session's outputs/, then in any attached Kaggle
input (e.g. the output of notebook 01 added as a data source), and only computed if
missing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import bus as B
from . import config as C
from . import wards as W


def find_output(rel: str) -> Path | None:
    p = C.paths()
    cand = [p["out"] / rel]
    if p["env"] == "kaggle":
        cand += [Path(x) for x in C.kaggle_glob(f"outputs/{rel}")]
    for c in cand:
        if c.exists():
            return c
    return None


_ROUTER = None


def router():
    global _ROUTER
    if _ROUTER is None:
        from . import data as D
        _ROUTER = B.WalkRouter(D.metro_stations(), cutoff_m=C.CORRIDOR_M)
    return _ROUTER


def get_scores(snapshot: str = C.SNAPSHOT_BEFORE, catchment_m: int = C.CATCHMENT_M,
               corridor_m: int = C.CORRIDOR_M) -> pd.DataFrame:
    rel = f"tables/station_scores_{snapshot}_c{catchment_m}_y{corridor_m}.csv"
    f = find_output(rel)
    if f is not None:
        return pd.read_csv(f)
    r = router() if max(catchment_m, corridor_m) <= C.CORRIDOR_M else None
    sc = B.station_scores(snapshot, catchment_m, corridor_m, router=r)
    sc.to_csv(C.paths()["out"] / rel, index=False)
    return sc


def get_transfer_list() -> list[str]:
    f = find_output("frozen_transfer_stations.json")
    if f is not None:
        rec = json.loads(f.read_text())
        print(f"Frozen list from {f} (created {rec['created_utc']}, sha256 {rec['sha256'][:12]}...)")
        return rec["stations"]
    print("No frozen list found: computing it with the pre-specified rule (deterministic).")
    return B.freeze_transfer_list(get_scores())["station"].tolist()


def get_population(radius_m: int = 800) -> pd.Series:
    rel = f"tables/station_population_{radius_m}m.csv"
    f = find_output(rel)
    if f is not None:
        return pd.read_csv(f, index_col=0).iloc[:, 0]
    s = W.station_population(radius_m=radius_m)
    s.to_csv(C.paths()["out"] / rel)
    return s


def save_table(df: pd.DataFrame, name: str):
    path = C.paths()["tab"] / name
    df.to_csv(path, index=False)
    print("saved", path)
    return path


def save_fig(fig, name: str):
    path = C.paths()["fig"] / name
    fig.savefig(path, dpi=200, bbox_inches="tight")
    print("saved", path)
    return path
