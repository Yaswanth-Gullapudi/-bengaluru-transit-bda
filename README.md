# Big Data Analytics for Bengaluru Public Transport

**Team 15** · Gullapudi Yaswanth · Madhurashree M · Mahadhii Ganapathi Subramanian
**Guide:** Ms. Sangita Khare

A Big Data pipeline (Hadoop HDFS + Apache Spark 4 on Kaggle) that joins BMRCL metro ridership with 26 BMTC bus-network
snapshots, the OpenStreetMap walking network and polling-booth population. It describes the whole network and tests a
dated natural experiment: did BMTC bus links push metro riders onto the new Yellow Line (opened 11 Aug 2025)?

| Result | Value |
|---|---|
| Bus-link diversion to the Yellow Line (pre-registered) | +0.65% per SD, p = 0.64: no effect, holds in 22 checks |
| Frequency elasticity (headway 25 to 19 min) | 0.30 (DiD), 0.21 (synthetic control) |
| Bus-linked stations busier (cross-section) | +28.6% entries per SD, p = 0.005 |
| Next-day demand forecaster (Random Forest) | 8.1% smaller miss than "same hour last week"; 90% ranges hold 93.2% |
| Spark vs pandas (38.6 M rows, 4 cores) | 2.2x faster |
| Pink Line (opened 14 Nov 2026) | Bus-transfer list frozen and hashed before any ridership exists |

---

## 1. Run the interactive dashboard (5 minutes)

Needs Python 3.10 or newer.

```bash
git clone https://github.com/Yaswanth-Gullapudi/-bengaluru-transit-bda.git
cd -- -bengaluru-transit-bda
pip install -r requirements.txt
streamlit run dashboard/app.py
```

It opens at http://localhost:8501. On Windows you can instead double-click **`run_dashboard.bat`**.

13 pages: Overview, How it works, Line explorer (Purple, Green, Yellow, Pink), Network analytics, Station explorer,
Yellow Line test, Headway calculator, All lines, Machine learning, Demand forecaster, Spark scaling, Pink Line,
Data & reproducibility. Light or dark: menu (top right) > Settings > Theme.
The dashboard only reads the result files in `results/` and `extensions/`; it does not need Spark or the raw data.

**Web demo without installing anything:** open `demo/yellow_line_explorer.html` through a local server
(`python -m http.server 8000`, then http://localhost:8000/demo/yellow_line_explorer.html). Opening the file directly
works too, except the forecaster panel, which loads `forecast.json`.

## 2. Repository layout

| Folder | What is in it |
|---|---|
| `code/t15/` | The Python package: config, HDFS/Spark setup (`env.py`), data loaders, bus-link scores, panels, econometrics, MLlib, scaling, network analytics, extensions, all-lines analysis, forecaster |
| `code/notebooks_src/` | Notebook sources (`# %%` cells); `python code/build_notebooks.py` turns them into `code/notebooks/*.ipynb` |
| `code/notebooks/` | The 13 notebooks run on Kaggle (00-11 and 05b) |
| `results/NN/outputs/` | Tables (CSV) and figures (PNG) downloaded from each Kaggle notebook run |
| `extensions/outputs/` | Pink Line pre-registration (`frozen_pink_stations.json`, `preregistration_pink.md`) and local extension tables |
| `dashboard/` | Streamlit + Plotly dashboard |
| `demo/` | Yellow Line Explorer single-page web demo and its data |
| `docs/` | Project context, research proposals, novelty review, final idea |
| `data_raw/ward/`, `data_raw/opencity_bmrcl/` | OpenCity files that cannot be downloaded automatically |

## 3. Notebooks

| # | Notebook | Engine | Main outputs |
|---|---|---|---|
| 00 | Setup and data: download, start HDFS, ingest 26 GTFS snapshots as Parquet | HDFS, Spark | data checks |
| 01 | Bus-link score; freeze top-10 transfer stations (SHA-256) | pandas, OSMnx | `frozen_transfer_stations.json`, fig 1 |
| 02 | Origin-destination diversion test, bootstrap, randomisation, event study | Spark SQL, pyfixest | figs 2-3 |
| 03 | Time of day, September, headway elasticity, synthetic control | pyfixest | figs 4-5 |
| 04 | Bus supply over 26 snapshots, route changes | Spark SQL | figs 6-7 |
| 05 / 05b | MLlib: LR, RF, GBT x metro / bus / shuffled-bus features (full / fast grid) | Spark MLlib | fig 8 |
| 06 | Spark 1/2/4 cores vs pandas on 1-26 snapshots | Spark | fig 9 |
| 07 | 22 robustness checks | pyfixest | fig 10 |
| 08 | Booth population access by constituency, 2018 vs 2025 bus service | GeoPandas | figs 11-12 |
| 09 | Network analytics: data quality, routes, shared stops, connectivity, demand, CSV vs Parquet | Spark SQL | figs 13-17 |
| 10 | Extensions and all lines: Pink pre-registration, heterogeneity, second shock, integration index, new-station ML | Spark MLlib, pyfixest | fig 18 |
| 11 | Next-day demand forecaster, ranges, crowding warnings, anomalies, KMeans station types | Spark MLlib | fig 19 |

## 4. Re-run the pipeline on Kaggle (free)

1. Create a Kaggle account, verify your phone number (needed for internet in notebooks), and create an API token
   (Settings > API > Create New Token).
2. Make a private Kaggle dataset from the `code/` folder (call it `t15-code`), and another from `data_raw/ward/` (`t15-ward`).
3. Import `code/notebooks/00_setup_and_data.ipynb`, attach `t15-code`, turn Internet on, run it (about 15 min).
4. For notebooks 01-11: attach `t15-code` and the output of notebook 00 (and 01 and 08 for notebooks 10-11, `t15-ward` for 08),
   then run. Each notebook starts HDFS and reloads the data itself.
5. Download each notebook's `outputs/` into `results/NN/` to refresh the dashboard.

## 5. Run locally (optional, Linux/macOS/WSL recommended)

```bash
pip install -r requirements-pipeline.txt
python -c "import sys; sys.path.insert(0,'code'); from t15 import data; data.download_all()"   # about 1.2 GB
```

Then open the notebooks in Jupyter. HDFS needs Java; on a laptop the code falls back to local Parquet with Spark.

## 6. Data sources

BMRCL hourly and station-pair ridership (RTI; [Vonter/bmrcl-ridership-hourly](https://github.com/Vonter/bmrcl-ridership-hourly), verified identical to
[OpenCity](https://data.opencity.in/dataset/bmrcl-station-wise-ridership-data)) · BMRCL GTFS ([Vonter/bmrcl-gtfs](https://github.com/Vonter/bmrcl-gtfs)) ·
BMTC GTFS, 26 snapshots ([Vonter/bmtc-gtfs](https://github.com/Vonter/bmtc-gtfs)) · Bus-stop accessibility and booth population ([bmtc.vonter.top](https://bmtc.vonter.top/bus_stops_accessibility/)) ·
BMTC stops and routes by ward ([OpenCity](https://data.opencity.in/dataset/bus-stops-and-routes-map-by-ward)) · OpenStreetMap contributors.
Each source keeps its own licence (ridership data: ODbL with BMRCL copyright notes).
