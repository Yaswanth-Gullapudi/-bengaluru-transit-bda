"""Analysis panels built from the metro ridership tables (pandas, after Spark ETL)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from . import data as D


def old_stations() -> list[str]:
    s = D.metro_stations()
    return sorted(s.loc[~s["is_yellow_new"], "station"])


def add_band(df: pd.DataFrame) -> pd.DataFrame:
    df["band"] = df["hour"].map(C.band_of)
    return df


def od_panel(od: pd.DataFrame | None = None, by: str = "band", days=None,
             drop_rv_dest: bool = True) -> pd.DataFrame:
    """Balanced origin x destination x date x (band|hour) panel of trips between OLD stations.

    Origins: old stations (incl. RV Road). Destinations: old stations except RV Road
    (the interchange is mechanically affected). o != d. Missing cells are zeros.
    """
    od = od if od is not None else D.load_od()
    days = days or C.AUG_DAYS
    olds = old_stations()
    dests = [s for s in olds if not (drop_rv_dest and s == C.INTERCHANGE)]
    x = od[od["origin"].isin(olds) & od["dest"].isin(dests) & (od["origin"] != od["dest"])
           & od["date"].isin(days)].copy()
    if by == "band":
        x = add_band(x)
    key = ["origin", "dest", "date", by]
    x = x.groupby(key, as_index=False)["trips"].sum()
    times = sorted(x[by].unique())
    full = pd.MultiIndex.from_product([olds, dests, days, times], names=key).to_frame(index=False)
    full = full[full["origin"] != full["dest"]]
    x = full.merge(x, on=key, how="left").fillna({"trips": 0})
    x["post"] = x["date"].isin(C.POST_DAYS).astype(int)
    x["ltrips"] = np.log1p(x["trips"])
    # fixed-effect identifiers (integer codes are faster than strings)
    x["fe_o_t"] = pd.factorize(x["origin"] + "|" + x["date"] + "|" + x[by].astype(str))[0]
    x["fe_o_d"] = pd.factorize(x["origin"] + "|" + x["dest"] + "|" + x[by].astype(str))[0]
    x["fe_d_t"] = pd.factorize(x["dest"] + "|" + x[by].astype(str))[0]
    return x


def attach_exposure(panel: pd.DataFrame, scores: pd.DataFrame, side: str = "dest",
                    cols=("YellowLink", "YellowLinkDir", "Collinear", "BusTrips", "MetroHopsToRV"),
                    transfer: list[str] | None = None) -> pd.DataFrame:
    """Merge station exposure onto the panel (destination or origin side), with
    standardised versions (mean 0, sd 1 across the stations used) and post interactions."""
    sc = scores.set_index("station")
    for c in cols:
        v = panel[side].map(sc[c]).astype(float)
        st = sc.loc[panel[side].unique(), c].astype(float)
        panel[f"{c}_{side[0]}"] = v
        panel[f"z{c}_{side[0]}"] = (v - st.mean()) / (st.std() if st.std() > 0 else 1)
        panel[f"post_z{c}_{side[0]}"] = panel["post"] * panel[f"z{c}_{side[0]}"]
    panel[f"line_{side[0]}"] = panel[side].map(sc["lines"])
    if transfer is not None:
        panel[f"transfer_{side[0]}"] = panel[side].isin(transfer).astype(int)
        panel[f"post_transfer_{side[0]}"] = panel["post"] * panel[f"transfer_{side[0]}"]
    return panel


def origin_shift_table(transfer: list[str], od: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per origin: share of its trips going to the frozen bus-transfer stations and to the
    new Yellow stations, before (1-10 Aug) vs after (11-18 Aug), on weekdays only."""
    od = od if od is not None else D.load_od()
    od = od[od["origin"].isin(old_stations())].copy()
    dt = pd.to_datetime(od["date"])
    od = od[(dt.dt.dayofweek < 5) & (~od["date"].isin(list(C.EVENT_DAYS)))]
    od["period"] = np.where(od["date"].isin(C.POST_DAYS), "post", "pre")
    od["to_transfer"] = od["dest"].isin(transfer)
    od["to_yellow"] = od["dest"].isin(C.YELLOW_NEW)
    days = od.groupby("period")["date"].nunique()
    g = od.groupby(["origin", "period"]).apply(
        lambda d: pd.Series({"trips": d["trips"].sum(),
                             "to_transfer": d.loc[d["to_transfer"], "trips"].sum(),
                             "to_yellow": d.loc[d["to_yellow"], "trips"].sum()}), include_groups=False)
    g = g.unstack("period").fillna(0)
    out = pd.DataFrame(index=g.index)
    for per in ("pre", "post"):
        out[f"trips_per_day_{per}"] = g[("trips", per)] / days[per]
        out[f"share_transfer_{per}"] = g[("to_transfer", per)] / g[("trips", per)].replace(0, np.nan)
        out[f"share_yellow_{per}"] = g[("to_yellow", per)] / g[("trips", per)].replace(0, np.nan)
    out["d_share_transfer"] = out["share_transfer_post"] - out["share_transfer_pre"]
    out["d_share_yellow"] = out["share_yellow_post"] - out["share_yellow_pre"]
    out["is_transfer_origin"] = out.index.isin(transfer)
    return out.reset_index()


def station_panel(days, kinds=("entries", "exits"), stations: list[str] | None = None) -> pd.DataFrame:
    """Station x date x hour panel of entries and exits."""
    parts = [D.load_station_hourly(k).set_index(["station", "date", "hour"]) for k in kinds]
    x = pd.concat(parts, axis=1).fillna(0).reset_index()
    x = x[x["date"].isin(days)]
    if stations is not None:
        x = x[x["station"].isin(stations)]
    x = add_band(x)
    for k in kinds:
        x[f"l{k}"] = np.log1p(x[k])
    x["dow"] = pd.to_datetime(x["date"]).dt.dayofweek
    x["weekend"] = (x["dow"] >= 5).astype(int)
    x["fe_s_h"] = pd.factorize(x["station"] + "|" + x["hour"].astype(str))[0]
    x["fe_t_h"] = pd.factorize(x["date"] + "|" + x["hour"].astype(str))[0]
    return x
