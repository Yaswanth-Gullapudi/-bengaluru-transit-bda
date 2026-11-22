# Big Data Analytics for Bengaluru Public Transport

**Team 15** · Gullapudi Yaswanth · Madhurashree M · Mahadhii Ganapathi Subramanian
**Guide:** Ms. Sangita Khare

**Live dashboard:** https://bengaluru-transit-bda.streamlit.app/ (14 pages, no install)

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

## Architecture flow

```
+------------------------------------------------------------------------------+
|                              PUBLIC RAW DATASETS                             |
|  BMRCL RTI ridership: station-pair hourly (1-18 Aug 2025), station entries    |
|  and exits (Aug + Sep 2025) | 26 BMTC GTFS timetables (2024-2026) | BMRCL     |
|  GTFS | OpenStreetMap walk network | booth population | OpenCity ward files   |
|  | Open-Meteo hourly weather                                                  |
+------------------------------------------------------------------------------+
                                       |
                                       v
+------------------------------------------------------------------------------+
|        INGEST, VALIDATE AND CLEAN  (notebook 00, notebook 09 data quality)   |
|  download -> unzip -> type checks -> duplicates / missing / bad coordinates   |
|  -> broken references -> 7,128 incomplete bus trips flagged                   |
+------------------------------------------------------------------------------+
                                       |
                                       v
+------------------------------------------------------------------------------+
|                  HADOOP HDFS STORAGE LAYER  (Hadoop 3.3.6, Kaggle)           |
|  /t15/metro/{entries, exits, od, stations}            Parquet                |
|  /t15/gtfs/{stops,routes,trips,stop_times,calendar}/snapshot=<date>/          |
|  Hive-style partitions, 297 MB (Parquet 4.2x smaller than CSV)                |
+------------------------------------------------------------------------------+
          |                           |                            |
          v                           v                            v
+----------------------+  +------------------------+  +--------------------------+
|      SPARK SQL       |  |      SPARK MLlib       |  |  ECONOMETRICS (Python)   |
| station-pair panels  |  | LR / RF / GBT + CV     |  | fixed-effects OLS, PPML  |
| bus-stop joins       |  | shuffled-bus placebo   |  | wild bootstrap, random-  |
| network analytics    |  | demand forecaster      |  | isation inference, event |
| supply over 26 snaps |  | KMeans station types   |  | study, synthetic control |
+----------------------+  +------------------------+  +--------------------------+
          |                           |                            |
          +---------------------------+----------------------------+
                                       |
                                       v
+------------------------------------------------------------------------------+
|                VERIFIED OUTPUTS  (results/NN/outputs, 14 notebooks)          |
|  82 CSV tables, 22 figures, frozen station lists + SHA-256 pre-registration   |
+------------------------------------------------------------------------------+
                                       |
                                       v
+------------------------------------------------------------------------------+
|                         INTERACTIVE VISUALISATION LAYER                      |
|  dashboard/app.py: Streamlit + Plotly, 14 pages, light and dark              |
|  demo/yellow_line_explorer.html: single-page web demo                        |
+------------------------------------------------------------------------------+
```

## Technologies used

| Layer | Technology | Used for |
|---|---|---|
| Compute | Kaggle notebooks (4 vCPU, 30 GB RAM) | Free cloud runs of all 13 notebooks |
| Storage | Apache Hadoop 3.3.6, HDFS | Distributed storage of all data, partitioned by snapshot date |
| File format | Apache Parquet (vs CSV benchmark) | Columnar, compressed storage |
| Processing | Apache Spark 4.0, PySpark, Spark SQL | Joins, aggregations, panels over 38.6 M rows |
| Machine learning | Spark MLlib (LinearRegression, RandomForest, GBT, KMeans, CrossValidator) | Prediction, placebo tests, forecaster, clustering |
| Statistics | pyfixest, statsmodels, SciPy | Fixed effects, bootstrap, randomisation inference |
| Geospatial | OSMnx, NetworkX, GeoPandas, Fiona | Walking distances, booth population, catchments |
| Data handling | pandas, NumPy, PyArrow | Local tables and Parquet I/O |
| Visualisation | Plotly, Matplotlib, Streamlit | Dashboard and notebook figures |
| Web demo | HTML, CSS, JavaScript (no framework) | Yellow Line Explorer page |
| Reproducibility | Git, GitHub, Kaggle CLI, SHA-256 hashing | Version control, cloud runs, pre-registration |

## Genuine analytical findings

All figures come from the Kaggle runs in `results/`.

1. **No bus-mediated diversion in the first week.** Trips to destinations with stronger bus links to the new Yellow Line
   changed by +0.65% per SD (95% CI -2.1% to +3.4%, p = 0.64; wild bootstrap p = 0.85; randomisation p = 0.39). The
   pre-registered list of 10 transfer stations shows +0.24% (p = 0.95). The result holds in 22 robustness checks.
2. **Frequency moves riders.** When the Yellow Line headway fell from 25 to 19 minutes (10 Sep 2025), its entries rose
   8.7% (p < 0.0001): an elasticity of 0.30 (synthetic control 0.21), inside the published range of 0.28-0.6.
3. **Observational vs causal.** Bus-linked stations carry 28.6% more riders per SD (p = 0.005), as observational Bengaluru
   studies report, yet that link did not cause a short-run switch.
4. **A first sign once service improved.** After the headway cut the 10 transfer stations lost 1.3% of exits (p = 0.037,
   one of four tests: suggestive).
5. **Where feeders are missing.** The busiest stations with no feeder buses: Majestic (32,976 weekday entries), MG Road,
   Vidhana Soudha, Seetharampalya (no bus stop within 400 m) and Kengeri. New Yellow stations average 24 feeder trips a day vs 61-89 on old lines.
6. **Green riders adopted the Yellow Line 3x more than Purple riders** (5.4% vs 1.8% of trips), because RV Road is on the Green Line.
7. **Access.** The Yellow Line put 345,000 more people within 800 m of a station, while 4.92 million live within 400 m of a bus stop with a trip to the corridor.
8. **Bus data helps rank new stations.** For the 15 Yellow stations, Spark MLlib Random Forest ranks busyness with rank
   correlation 0.60 using real bus data vs 0.26 metro-only and 0.35 with shuffled bus data; it does not improve ridership levels.
9. **A working forecaster.** Next-day station-hour forecasts miss 8.1% less than "same hour last week", 90% ranges hold
   93.2% of unseen hours, crowding warnings are 85.8% precise (44 fewer false alarms). Weather (V3) and learning the
   weekly change (V2) did not reliably help.
10. **Network facts.** 4,130 routes and 9,309 stops; Majestic is served by 1,019 routes; only 5% of bus stops are within
    400 m of a metro station; weekday bus trips grew 42% from Jan 2024 to Nov 2026; scheduled bus speed is 15.8 km/h.
11. **Spark scaling.** On 38.6 M rows Spark with 4 cores took 22.5 s vs 50.3 s for pandas (2.2x); on one snapshot pandas was faster.

## Fare revenue and economic effect

From BMRCL's own fare and revenue fields (notebook 12), weekday averages:

| Measure | Before (1-10 Aug) | After (11-18 Aug) | Change |
|---|---|---|---|
| Trips per weekday | 699,503 | 796,124 | +13.8% |
| **Fare revenue per weekday** | **Rs 3.27 crore** | **Rs 3.83 crore** | **+17.2%** |
| Average fare | Rs 46.7 | Rs 48.1 | +2.9% |
| Revenue from trips not using new stations | Rs 3.27 crore | Rs 3.37 crore | +3.1% |

- Trips using the new Yellow stations bring **Rs 45.8 lakh per weekday (12% of revenue)** at an average fare of Rs 56.8, because they are longer trips.
- The **10 Sep headway cut** adds about **Rs 2.2 lakh per weekday, about Rs 5.4 crore a year** (+8.7% entries x 48,414 weekday entries x Rs 51.4).
- This is fare-box revenue, not profit (operating costs are not public), and it leaves out passengers' time savings. Each period has 5 weekdays.

---

## 1. Run the interactive dashboard

Open the live version at **https://bengaluru-transit-bda.streamlit.app/**, or run it on your own PC (5 minutes):

Needs Python 3.10 or newer.

```bash
git clone https://github.com/Yaswanth-Gullapudi/-bengaluru-transit-bda.git
cd -- -bengaluru-transit-bda
pip install -r requirements.txt
streamlit run dashboard/app.py
```

It opens at http://localhost:8501. On Windows you can instead double-click **`run_dashboard.bat`**.

14 pages: Overview, How it works, Line explorer (Purple, Green, Yellow, Pink), Network analytics, Station explorer,
Yellow Line test, Headway calculator, All lines, Machine learning, Demand forecaster, Fare revenue, Spark scaling,
Pink Line, Data & reproducibility. Light or dark: menu (top right) > Settings > Theme.
The dashboard only reads the result files in `results/` and `extensions/`; it does not need Spark or the raw data.

**Web demo without installing anything:** open `demo/yellow_line_explorer.html` through a local server
(`python -m http.server 8000`, then http://localhost:8000/demo/yellow_line_explorer.html). Opening the file directly
works too, except the forecaster panel, which loads `forecast.json`.

## 2. Repository layout

| Folder | What is in it |
|---|---|
| `code/t15/` | The Python package: config, HDFS/Spark setup (`env.py`), data loaders, bus-link scores, panels, econometrics, MLlib, scaling, network analytics, extensions, all-lines analysis, forecaster |
| `code/notebooks_src/` | Notebook sources (`# %%` cells); `python code/build_notebooks.py` turns them into `code/notebooks/*.ipynb` |
| `code/notebooks/` | The 14 notebooks run on Kaggle (00-12 and 05b) |
| `results/NN/outputs/` | Tables (CSV) and figures (PNG) downloaded from each Kaggle notebook run |
| `extensions/outputs/` | Pink Line pre-registration (`frozen_pink_stations.json`, `preregistration_pink.md`) and local extension tables |
| `dashboard/` | Streamlit + Plotly dashboard |
| `demo/` | Yellow Line Explorer single-page web demo and its data |
| `docs/` | Full project report (`Project_Report.md`), project context, research proposals, novelty review, final idea |
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
| 11 | Next-day demand forecaster (V1-V3), ranges, crowding warnings, anomalies, KMeans station types | Spark MLlib | fig 19 |
| 12 | Fare revenue before/after the opening, by line, from the headway cut | pandas | fig 20 |

## 4. Re-run the pipeline on Kaggle (free)

1. Create a Kaggle account, verify your phone number (needed for internet in notebooks), and create an API token
   (Settings > API > Create New Token).
2. Make a private Kaggle dataset from the `code/` folder (call it `t15-code`), and another from `data_raw/ward/` (`t15-ward`).
3. Import `code/notebooks/00_setup_and_data.ipynb`, attach `t15-code`, turn Internet on, run it (about 15 min).
4. For notebooks 01-12: attach `t15-code` and the output of notebook 00 (and 01 and 08 for notebooks 10-11, `t15-ward` for 08),
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
