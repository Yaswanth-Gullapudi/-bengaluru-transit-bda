"""Project-wide constants and paths for the Team 15 Yellow Line study.

Works on Kaggle, Colab and a local machine. Paths are resolved by `paths()`.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------- data sources
METRO_REPO_RAW = "https://github.com/Vonter/bmrcl-ridership-hourly/raw/main"
METRO_FILES = {
    "entries": "data/station-hourly.parquet",          # 1-18 Aug + 1-30 Sep 2025
    "exits": "data/station-hourly-exits.parquet",      # 1-18 Aug + 1-30 Sep 2025
    "od": "data/stationpair-hourly-enhanced.parquet",  # 1-18 Aug 2025
}
METRO_GTFS_URL = "https://github.com/Vonter/bmrcl-gtfs/raw/main/gtfs/bmrcl.zip"
BMTC_GTFS_URL = "https://github.com/Vonter/bmtc-gtfs/raw/{sha}/gtfs/bmtc.zip"

# Every commit of Vonter/bmtc-gtfs that changed gtfs/bmtc.zip (snapshot date -> commit).
BMTC_SNAPSHOTS = {
    "2024-01-05": "c274bf102c", "2024-02-20": "be648c4176", "2024-03-26": "679626fdab",
    "2024-10-16": "3b4a155d66", "2025-02-24": "a7a6bda613", "2025-04-09": "6aecd67848",
    "2025-06-18": "1af0dee835", "2025-08-04": "6077c6a902", "2025-09-02": "5b22150afc",
    "2025-10-23": "e82acdbc12", "2025-11-02": "d6334a4dd9", "2025-12-02": "17e4d7fc6e",
    "2026-01-01": "dfb4032944", "2026-02-09": "f8a331633d", "2026-02-28": "11b82d778e",
    "2026-03-10": "71c738a0fd", "2026-04-03": "435742bb22", "2026-05-03": "4dc95a2480",
    "2026-05-27": "1a4717a7d4", "2026-06-05": "1e50f453af", "2026-06-18": "9ad23ab5a1",
    "2026-07-06": "afb09da501", "2026-07-12": "9b10e7bacb", "2026-09-07": "7e7c64f9b4",
    "2026-11-04": "a90e6ff8fe", "2026-11-09": "4ced54ed79",
}
SNAPSHOT_BEFORE = "2025-08-04"   # bus network one week before the opening (exposure)
SNAPSHOT_AFTER = "2025-09-02"    # bus network three weeks after

# ---------------------------------------------------------------- study design
OPENING_DATE = "2025-08-11"      # first public service on the Yellow Line
INTERCHANGE = "Rashtreeya Vidyalaya Road"   # RV Road, only Green-Yellow interchange
# The 15 Yellow Line stations that are new on 11 Aug 2025 (RV Road already existed).
YELLOW_NEW = [
    "Ragigudda", "Jayadeva Hospital", "BTM Layout", "Central Silk Board", "Bommanahalli",
    "Hongasandra", "Kudlu Gate", "Singasandra", "Hosa Road", "Beratena Agrahara",
    "Electronic City", "Infosys Foundation Konappana Agrahara", "Huskur Road",
    "Biocon Hebbagodi", "Delta Electronics Bommasandra",
]
AUG_DAYS = [f"2025-08-{d:02d}" for d in range(1, 19)]
PRE_DAYS = AUG_DAYS[:10]          # 1-10 Aug (10 Aug = inauguration, closed to public)
POST_DAYS = AUG_DAYS[10:]         # 11-18 Aug
SEP_DAYS = [f"2025-09-{d:02d}" for d in range(1, 31)]
HEADWAY_CUT_DATE = "2025-09-10"   # 4th train: 25 -> 19 min; first train 6:30 -> 6:00
HEADWAY_BEFORE, HEADWAY_AFTER = 25.0, 19.0

# Days with known city-wide or local disturbances (used in robustness checks).
EVENT_DAYS = {
    "2025-08-08": "Varamahalakshmi festival (low ridership)",
    "2025-08-15": "Independence Day (holiday)",
    "2025-08-16": "Janmashtami",
}
FLOWER_SHOW_STATIONS = ["Lalbagh"]          # Lalbagh flower show ~7-18 Aug
FESTIVAL_STATIONS = ["Mahalakshmi"]         # ISKCON crowd on Janmashtami
JOYRIDE_DAYS = ["2025-08-11", "2025-08-12"]
PLACEBO_DATES = ["2025-08-05", "2025-08-07"]
REFERENCE_DAY = "2025-08-07"      # last normal pre-opening weekday (event-study base)

# Time bands for the origin-destination panel.
BANDS = {"am_peak": range(7, 11), "midday": range(11, 16), "pm_peak": range(16, 21)}
BAND_OTHER = "other"

# Catchment radii (metres, along the walking network).
CATCHMENT_M = 400
CORRIDOR_M = 800
TOP_K_TRANSFER = 10
SEED = 15


def band_of(hour: int) -> str:
    for name, hours in BANDS.items():
        if hour in hours:
            return name
    return BAND_OTHER


# ---------------------------------------------------------------- environment
def kaggle_glob(pattern: str) -> list[str]:
    """Recursive search under /kaggle/input that follows symlinks (pathlib's ** does not on 3.13)."""
    import glob
    return sorted(glob.glob(f"/kaggle/input/**/{pattern}", recursive=True))


def env() -> str:
    if os.path.exists("/kaggle"):
        return "kaggle"
    if os.path.exists("/content"):
        return "colab"
    return "local"


def paths() -> dict:
    """Where raw data, outputs and HDFS live in the current environment."""
    e = env()
    if e == "kaggle":
        work = Path("/kaggle/working")
        # datasets / notebook outputs may be mounted 1-3 levels deep
        inputs = sorted({Path(m).parent.parent for m in kaggle_glob("metro/station-hourly.parquet")})
        inputs = [i.parent if i.name == "data_raw" else i for i in inputs]
    elif e == "colab":
        work = Path("/content")
        inputs = []
    else:
        work = Path(__file__).resolve().parents[2]  # Team15_research/
        inputs = []
    if os.environ.get("T15_WORK"):          # override output location (used for tests)
        work = Path(os.environ["T15_WORK"])
    raw = Path(os.environ.get("T15_RAW", work / "data_raw"))
    # Prefer a read-only Kaggle Dataset copy of the raw files if one is attached.
    for d in inputs:
        if (d / "data_raw" / "metro").exists():
            raw = d / "data_raw"
            break
        if (d / "metro").exists():
            raw = d
            break
    out = work / "outputs"
    for sub in ("", "figures", "tables", "cache"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    return {
        "env": e,
        "work": work,
        "raw": raw,
        "raw_writable": work / "data_raw",
        "out": out,
        "fig": out / "figures",
        "tab": out / "tables",
        "cache": out / "cache",
        "hdfs_root": os.environ.get("T15_HDFS", "hdfs://localhost:9000/t15"),
    }
