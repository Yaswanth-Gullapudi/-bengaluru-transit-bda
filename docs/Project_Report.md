# Bus Links and Bengaluru's Yellow Line: A Pre-registered Big-Data Test

Team 15 · Gullapudi Yaswanth, Madhurashree M, Mahadhii Ganapathi Subramanian · Advisor: Ms. Sangita Khare

Nov 21, 2026 · @Yaswanth

## Abstract

Bus links did not redirect metro riders toward Bengaluru's new Yellow Line in its first five weeks; train frequency did. The Yellow Line (RV Road to Bommasandra, 15 new stations) opened on 11 August 2025. We asked whether old metro stations that are well connected by BMTC buses to the new corridor sent more trips to it. We joined 12.06 million origin-destination metro trips (1-18 Aug 2025), 92,280 station-hours of entries and exits (Aug-Sep 2025), 26 BMTC GTFS snapshots (38.6 million stop-time rows), OpenStreetMap walking paths and 2022 polling-booth population.

The bus-link score of each station was computed from the bus network alone, and the 10 most bus-linked stations were frozen with a SHA-256 hash before any ridership was analysed.

- **Main test (pre-registered):** +0.65% more trips to destinations per 1 SD of bus-link score after opening (95% CI -2.1% to +3.4%, p = 0.64; wild-cluster bootstrap p = 0.85; randomisation p = 0.39). The frozen transfer stations show +0.24% (p = 0.95). The result holds across 22 robustness checks.
- **Headway cut (10 Sep, 25 to 19 min):** Yellow Line entries rose 8.7% (p < 0.0001), a frequency elasticity of 0.30; synthetic control gives 0.21.
- **Bus response:** BMTC added the MF-22 metro-feeder family (about 100 trips a day) along the corridor.
- **Access:** the line put 345,000 more people within 800 m of a station, while 4.92 million live within 400 m of a bus stop with a trip to the corridor.
- **Network analytics (proposal scope):** the BMTC network has 4,130 routes and 9,309 stops (Aug 2025); Majestic is served by 1,019 routes; only 5% of stops lie within 400 m of a metro station; weekday bus trips grew 42% from Jan 2024 to Nov 2026. Parquet on HDFS is 4.2x smaller and 3-4x faster than CSV.
- **Extensions:** bus-linked stations are 29% busier per SD in the cross-section (p = 0.005), yet showed no first-week diversion; no origin type or substitute pair responds significantly; after the 10 Sep headway cut transfer stations lost 1.3% of exits (p = 0.037). A second event, the Pink Line (opened 14 Nov 2026), is pre-registered with a frozen, hashed list.
- **Demand forecaster and interactive layer:** a Spark MLlib Random Forest forecasts next-day entries at every station and hour with an average miss 8.1% smaller than "same hour last week", 90% ranges that hold 93.2% of the time, and crowding warnings at 86% precision. A Streamlit + Plotly dashboard (13 pages, including a per-line explorer and a plain-language how-it-works page, in light and dark themes) and a web demo present every result from the pipeline's output files.
- **Fare revenue:** weekday fare revenue rose 17.2% after the opening (Rs 3.27 to 3.83 crore a day); Yellow Line trips bring Rs 45.8 lakh a day, and the headway cut is worth about Rs 5.4 crore a year in fares.
- **Big Data:** ingestion and joins run on HDFS and Spark 4 on Kaggle. Spark with 4 cores processed 26 snapshots in 22.5 s against 50.3 s for pandas.
- **Machine learning:** Spark MLlib compares Linear Regression, Random Forest and Gradient-Boosted Trees with and without bus features, against a shuffled-bus placebo. Random Forest predicts September ridership with R-squared 0.96, but bus features cut test error by at most 1.6% and do not reliably beat the placebo.

## 1 Introduction and problem definition

Most Bengaluru transit studies look at metro ridership or bus ridership on its own; this project joins both to test one question about a real event. Namma Metro (BMRCL) carries over 800,000 trips a day and BMTC buses carry several million, yet the two networks are planned and studied separately. When a new metro line opens, the bus network decides who can reach it and which older trips it replaces.

### 1.1 The natural experiment

The Yellow Line was inaugurated on 10 August 2025 and opened to the public on 11 August 2025. It runs 19.15 km from RV Road (an interchange with the Green Line) to Bommasandra along Hosur Road, through Silk Board and Electronic City, a corridor previously served only by buses. It opened with 3 trains at a 25-minute headway. On 10 September 2025 a fourth train cut the headway to 19 minutes and the first train moved to 6:00 am.

Before the line opened, many commuters to Electronic City rode the metro to a station such as Banashankari or Chickpete and then took a bus. If the Yellow Line replaced that bus leg, trips to those bus-transfer stations should fall and trips routed via RV Road should rise.

### 1.2 Research questions

1. **RQ1 (pre-registered):** After 11 Aug 2025, did old metro stations with stronger bus links to the Yellow corridor lose trips relative to other destinations from the same origin?
2. **RQ2:** Does any shift show the commuter time-of-day signature (fewer AM exits and PM entries at transfer stations), and does it persist into September?
3. **RQ3:** How strongly did Yellow Line ridership respond to the 10 Sep headway cut (frequency elasticity)?
4. **RQ4:** How did BMTC change its bus supply around the corridor across 26 network snapshots (Jan 2024 to Nov 2026)?
5. **RQ5:** Do bus-network features improve Spark MLlib predictions of post-opening station ridership beyond metro-only features and a shuffled placebo?
6. **RQ6:** How many people gained direct metro access, and how many can reach the line by bus?
7. **RQ7 (systems):** How do Spark and HDFS scale for multi-snapshot GTFS processing compared with single-machine pandas?

### 1.3 Contributions

- The first station and origin-destination level causal test of an Indian metro line opening, using public RTI ridership data.
- A bus-link score built only from dated open GTFS data, with the treatment list frozen and hashed before ridership was examined.
- A credible null result for bus-mediated diversion, with wild-cluster bootstrap and randomisation inference, plus a positive frequency elasticity.
- An end-to-end Big Data pipeline (HDFS, Spark SQL, Spark MLlib) on free cloud compute, with a scaling benchmark and a placebo-controlled ML comparison.

## 2 Literature survey

Each building block of this study is published, but no peer-reviewed study has tested an Indian metro line opening at station or origin-destination level with bus-network exposure. The table groups the closest work by theme.

| Theme | Key studies | What they show | Gap this project fills |
| --- | --- | --- | --- |
| Metro and bus competition in Bengaluru | Hasan, Nirmale, Deepa and Pinjari 2025 (TR-A 200:104638); Deepa et al. 2022 (TR-A 163); Gadepalli et al. 2022 (CSTP 10); CiSTUP-BMTC booklet 2023; CSTEP report on metro impact on bus | Feeder routes raise and parallel routes lower metro ridership; bus routes overlapping metro lose riders; about 38% of metro users came from BMTC | All observational, no exogenous shock; no test around a line opening |
| Bus overlap as a moderator of metro effects | Chai, Sun and Yin 2025 (TR-A 199); Liu et al. 2026 (TR-A 212); Gao et al. 2022 | Metro-bus spatial overlap moderates bus ridership loss across Chinese cities | City-level panels; nothing at station or OD level, nothing in India |
| New lines redistributing existing ridership | Lu et al. 2026 (JPER 46); Ding et al. 2025 (JTG 125); Park et al. 2016; Fu et al. 2018 (J. Adv. Transp.) | Existing stations gain or lose flow when a line opens, especially transfer stations | Bus links not modelled as the channel |
| Ridership prediction with transport features | Ding et al. 2024 (Metro-MGAT); Lim 2025 (MIT thesis); Kori and Srikanth 2025 | GTFS competing/complementary route variables improve direct-demand models | No placebo test of whether station-level features act as station IDs |
| Accessibility before and after a new line | Oslo Fornebu (Findings); Brussels Metro 3 (arXiv 2509.22223); Guangzhou 2026; Bengaluru ward equity (CSTP 2022); Bengaluru feeder equity 2026 | GTFS-based access gains and equity | Population at booth level, not ward level |
| Yellow Line specifically | IISc Yellow Line project report 2026 (commuter survey); Diagram Chasing blog 2025 (station before/after) | The blog states the bus-transfer hypothesis but runs only per-station regressions | Our study tests it formally, pre-registered, with OD fixed effects |
| Big Data for transit | Wang et al. 2021; Brands et al. 2020 (EJTIR); Spark-based GTFS and smart-card pipelines | Distributed processing of large transit feeds | Applied here to 26 dated GTFS snapshots with a measured scaling curve |

**Where this study sits.** Prior Bengaluru work shows that buses compete with and feed the metro, but it cannot separate cause from geography. City-level panels show overlap matters but cannot say which stations or trips move. This study uses a dated shock, a pre-committed exposure measure, and origin-by-date fixed effects that absorb every shock specific to an origin station on a day.

**Lessons taken from the literature.**

- Pre-register one primary specification, because many exposure variants invite a specification search.
- Report the correlation between bus exposure and plain metro geography (distance to RV Road), since a high value would make the bus claim unidentifiable.
- Treat the Lalbagh flower show (about 7 to 18 Aug 2025) and opening-week joyriding as local shocks, and test robustness without them.
- Drop the 6-7 am hour when studying the 10 Sep headway change, because the first train moved earlier the same day.

### 2.1 Papers from the team's literature survey, and how this project compares

| # | Paper | What it did | What this project matches or adds |
| --- | --- | --- | --- |
| 1 | Adhvaryu, Chopde and Dashora 2019, Surat PTAL (CSTP 7) | Mapped public transport accessibility against population density | Booth-level access for 10.13 M people, before and after a new line, by walking network (Section 6.6) |
| 2 | Miftah et al. 2025, Big Data for urban traffic | Hadoop and Spark for real-time traffic; 15-25% travel-time savings | Same stack (HDFS, Spark) with a measured scaling curve and a CSV vs Parquet test (Sections 5A, 8) |
| 3 | Wang et al. 2023, Beijing bus-metro network (CIS 9) | Combined bus and subway network; connectivity-based optimisation | Bus-metro link score for every station; route connectivity graph of 1.53 M route pairs (Sections 5, 5A) |
| 4 | Melo et al. 2024, Porto demand-responsive transport | Mobile data and simulation to redesign routes | Feeder-route supply response and feeder gaps by constituency (Sections 6.5, 10.2) |
| 5 | Ushakov et al. 2022, Big Data in smart-city transport | Review of Big Data for infrastructure capacity | Applied, with a working pipeline and results |
| 6 | Nesmachnow et al. 2023, Montevideo travel times | Bus travel times from multiple sources; 18 km/h average, 10.5-13.9% peak delay | Scheduled BMTC speed: median 15.8 km/h, 15.3 at peaks vs 22.8 at night (Section 5A) |
| 7 | Rakesh et al. 2018, Big Data at BMTC | Case study of BMTC's tracking, ticketing and passenger information systems | Uses the open GTFS that came out of that tracking system; notes its gaps (13% incomplete trips) |
| 8 | Oladimeji et al. 2023, smart transportation overview | IoT, ML and cloud technologies for transport | Spark MLlib with a placebo test of feature value (Section 7) |
| 9 | Yadav 2025, public transport optimisation survey | Real-time analytics strategies; data-integration gaps | Integrates bus, metro, walking network and population in one pipeline |

The survey's four research gaps (no integrated processing, fragmented data, little Bengaluru network analysis, bus and metro studied separately) are each answered: one HDFS pipeline, cleaned and joined data, Bengaluru network analytics, and a joint bus-metro test. Beyond the surveyed papers, this project adds causal identification (a dated natural experiment), pre-registration, and formal inference.

## 3 Data sources

Six public datasets, about 1.2 GB raw and 297 MB as Parquet on HDFS, are joined at station, stop and polling-booth level. All are openly downloadable; no data was collected by the team.

| Dataset | Source | Coverage | Size | Used for |
| --- | --- | --- | --- | --- |
| BMRCL station-hourly entries | RTI release, GitHub Vonter/bmrcl-ridership-hourly | 83 stations; 1-18 Aug and 1-30 Sep 2025 (48 days) | 92,280 station-hours | Time of day, September, headway, MLlib target |
| BMRCL station-hourly exits | same | same | 95,616 station-hours | Time-of-day signature |
| BMRCL station-pair (OD) hourly | same | 1-18 Aug 2025 | 1,273,629 rows; 12,059,475 trips | Main diversion test |
| BMRCL metro GTFS | BMRCL open GTFS | 83 stations (Purple 36, Green 30, Yellow 15, 2 interchanges) with entrances | 2.3 MB | Station locations, lines, hops to RV Road |
| BMTC bus GTFS, 26 dated snapshots | GitHub Vonter/bmtc-gtfs commit history | 5 Jan 2024 to 9 Nov 2026; 42,065 to 69,642 weekday trips each | 1.1 GB zipped; 38.6 M stop-time rows | Bus-link score, bus supply, scaling benchmark |
| BMTC bus-stop accessibility and booth population | bmtc.vonter.top | 29 assembly constituencies, 8,778 polling booths, 10.13 M people (2022 rolls) | 79 MB GeoJSON | Population access, ML feature |
| BMTC stops and routes by ward (2018) | OpenCity data portal | 28 constituency stop files with trip counts, plus a routes file | 29 CSV files | 2018 vs 2025 service comparison |
| OpenStreetMap walking network | OSMnx | Bengaluru metro area bounding box | 214,585 nodes, 555,054 edges | Walking distances, 400 m and 800 m catchments |

**Daily ridership around the opening.** Metro trips rose from about 0.71 M on a pre-opening weekday (4 Aug) to 0.79 M on opening Monday (11 Aug) and 0.84 M on 14 Aug, from the OD file aggregated in Spark SQL.

**Data caveats.**

- The OD file covers only 1-18 Aug 2025: 10 pre-opening days and 8 post-opening days. September has station totals but no OD pairs.
- BMTC GTFS includes only routes with working live tracking, and stop times are interpolated. Snapshot differences can reflect tracking coverage as well as real service changes.
- The 2018 OpenCity counts come from a different system than 2025 GTFS, so the 2018 vs 2025 comparison is indicative only.
- Booth population is voters (adults on the 2022 roll), not total residents.

**Source verification (OpenCity, as named in the proposal).** The BMRCL ridership files on the [OpenCity data portal](https://data.opencity.in/dataset/bmrcl-station-wise-ridership-data) were downloaded and matched cell by cell against the GitHub copy used in the pipeline. They are identical: September entries 21,721,271 and exits 21,667,826 (1-30 Sep), and August entries 12,116,611 (1-18 Aug), for all 83 stations, with zero difference in every date-hour. Both copies come from the same BMRCL RTI response; the pipeline reads the GitHub Parquet version because it is already cleaned and includes the station-pair file.

## 4 Big Data architecture

The pipeline runs entirely on free Kaggle CPU notebooks: one notebook loads all data into HDFS once, and twelve analysis notebooks (01-11 and 05b) read from it through Spark.

&#91;embedded content: pipeline architecture · notebooks 00-08 on Kaggle\]

Data flows top to bottom. Notebooks 01-11 attach notebook 00's output as a Kaggle input, so each analysis starts from the same stored data.

| Layer | Technology | Why it was chosen |
| --- | --- | --- |
| Compute | Kaggle notebooks, 4 vCPU, about 30 GB RAM, internet on, 12-hour limit | Free, reproducible, runs several notebooks in parallel |
| Storage | HDFS 3.3.6, single NameNode + DataNode, replication 1, 64 MB blocks | Distributed file system required by the course; Parquet files partitioned by snapshot date |
| Processing | Apache Spark 4.0 (PySpark), local mode with 1, 2 or 4 cores | Spark 4 needed for Python 3.13 on Kaggle; SQL joins and aggregations over 38.6 M stop-time rows |
| Machine learning | Spark MLlib Pipelines, OneHotEncoder, VectorAssembler, CrossValidator | Distributed model training and k-fold tuning inside Spark |
| Statistics | pyfixest (high-dimensional fixed effects), custom wild-cluster bootstrap and randomisation inference | Spark has no fixed-effects estimator with clustered inference |
| Geospatial | OSMnx, NetworkX multi-source Dijkstra, GeoPandas | Network walking distance instead of straight-line buffers |
| Orchestration | Kaggle CLI from a laptop: dataset versions, kernel push, status, output download | Scripted runs across accounts |

### 4.1 Storage layout on HDFS

- `/t15/gtfs/<table>/snapshot=<date>/` holds stops, trips, routes and stop\_times for each of the 26 snapshots (Hive-style partitioning, so Spark prunes by date).
- `/t15/metro/` holds the three ridership tables and station metadata as Parquet.
- Ingesting all 26 snapshots took 244 to 261 s; total size is 290.8 MB for GTFS and 6.0 MB for metro.

### 4.2 Engineering decisions

- HDFS runs with `hdfs --daemon` as root, without SSH, so it starts inside a notebook. If it fails, the code falls back to local Parquet and says so in the log.
- GTFS zips are unpacked to a temporary local folder, converted to Parquet and written to HDFS, so raw text never sits in HDFS.
- The walking graph is built once for one bounding box (about 6 minutes) and cached, instead of one download per station (about 100 s each).
- All random steps use seed 15, and the frozen station list carries a SHA-256 hash, so results can be checked later.
- Each notebook saves its tables and figures under `outputs/`, which Kaggle stores with the notebook version.

## 5 Methodology

The method has nine steps. Steps 1 and 2 use only the bus network and are fixed before any ridership is opened; steps 3 to 9 test, explain and stress the result.

### 5.1 Step 1: bus-link score for every metro station (notebook 01)

For each station s, all weekday bus trips stopping within a 400 m walk of any station entrance were found, using network walking distance on the OSM graph. Each score uses the 4 Aug 2025 GTFS snapshot, one week before opening.

| Score | Definition |
| --- | --- |
| BusTrips | Weekday bus trips stopping within 400 m walk of s |
| BusRoutes | Distinct routes among those trips |
| BusStops | Distinct bus stops within the catchment |
| YellowLink (primary) | Share of those trips that also stop within 800 m of a new Yellow Line station |
| YellowLinkDir | Same, counting only trips that reach the corridor after passing s |
| YellowLinkTrips | Number of linking trips |
| Collinear | Mean number of corridor stops each trip visits (route overlap with the corridor) |
| near\_corridor | True if s's own catchment already contains corridor stops |
| MetroHopsToRV | Metro stations travelled from s to RV Road (pure metro geography) |

Sensitivity versions use 800 m catchments, a 400 m corridor and the 2 Sep 2025 snapshot.

### 5.2 Step 2: frozen transfer list (pre-registration)

The 10 old stations with the highest YellowLink were frozen, excluding RV Road and any station whose catchment touches the corridor. The list, the rule and a SHA-256 hash were saved at 12:17 UTC on 21 Nov 2026, before any ridership notebook ran. Kaggle's version history records that order. OSF registration was not possible for the team, so the Kaggle record serves as the timestamp.

Frozen list: Lalbagh, Kundalahalli, Sri Sathya Sai Hospital, Indiranagar, Nallurahalli, Krishnarajapura, South End Circle, Benniganahalli, Pattandur Agrahara, Banashankari (hash 2ea7ed4b...a7a9).

### 5.3 Step 3: origin-destination diversion test (notebook 02, primary)

The OD file was aggregated in Spark SQL into a balanced panel of trips from origin o to destination d on date t in time band b (AM peak 7-10, midday 11-15, PM peak 16-20). Only old-to-old station pairs are used, so Yellow Line trips themselves are excluded.

```latex
\log(1 + \mathrm{trips}_{odtb}) = \alpha_{otb} + \gamma_{odb} + \beta \, \mathrm{Post}_t \times z\mathrm{YellowLink}_d + \varepsilon_{odtb}
```

- The origin-by-date-by-band effect absorbs every shock to an origin station on a given day, such as weather, events or its own access.
- The pair-by-band effect absorbs each pair's normal level.
- zYellowLink is the standardised score of the destination; Post marks 11-18 Aug.
- If bus-linked destinations lost riders to the Yellow Line, beta is negative.
- Standard errors are clustered by destination (68 clusters). The sample is 323,208 pair-date-band cells.

A second version replaces zYellowLink with a 0/1 indicator for the frozen transfer stations. PPML (Poisson) versions use raw counts instead of logs.

### 5.4 Step 4: inference that does not rely on large-sample theory

- **Wild-cluster bootstrap** (Webb weights, 9,999 draws) by destination, because 68 clusters is few.
- **Randomisation inference** (1,000 permutations): the bus-link scores are shuffled across destinations, the model is re-fitted after fixed-effect demeaning, and the share of shuffled betas as large as the real one is the p-value.
- **Event study:** separate coefficients for each day, with 7 Aug as reference, to check pre-trends.
- **Cross-origin matching:** whether origins that sent more trips to transfer stations before opening gained more Yellow share after (Spearman correlation and weighted regression).
- **Naive comparison:** a simple station before/after percentage change, set against the fixed-effects estimate.

### 5.5 Step 5: time-of-day signature and September persistence (notebook 03)

If metro-plus-bus commuters moved to the Yellow Line, transfer stations should lose AM-peak exits and PM-peak entries. Station-hour panels of log entries and exits were fitted with station-by-hour and date-by-hour fixed effects and post x band x exposure terms. The same model was extended to 1-30 Sep, overall and week by week.

### 5.6 Step 6: headway elasticity (notebook 03)

Yellow stations were compared with all other stations before and after 10 Sep (difference-in-differences, station-by-hour and date-by-hour fixed effects). The 6 am hour was dropped because the first train moved to 6:00 that day. The elasticity is beta divided by ln(25/19) = 0.274. A synthetic control, built from demeaned donor stations, checks the estimate.

### 5.7 Step 7: bus supply response (notebook 04)

Spark counted weekday trips by route and stop across all 26 snapshots. An event study on supply near Yellow stations, and a route-by-route diff of 4 Aug vs 2 Sep 2025, show how BMTC adjusted (including MF metro-feeder routes).

### 5.8 Step 8: population access (notebook 08)

Each polling booth's adult population was assigned to stations by walking distance (400 m and 800 m). The share of people within 800 m of a station before and after the Yellow Line, and within 400 m of a bus stop with a trip to the corridor, were computed by constituency. The 2018 OpenCity stop files were matched to 2025 GTFS stops within 100 m.

### 5.9 Step 9: Spark MLlib comparison and scaling (notebooks 05 and 06)

Section 7 describes the ML design and Section 8 the scaling benchmark.

## 5A Network analytics: the BDA framework from the proposal

Before testing the Yellow Line, notebook 09 describes the whole network in Spark, delivering every analysis named in the original proposal. Main snapshot: 4 Aug 2025; history: all 26 snapshots.

### Data quality and cleaning

| Table | Raw rows | Issue found | Rows affected | Action |
| --- | --- | --- | --- | --- |
| Bus stops | 9,309 | Duplicates, missing or out-of-area coordinates | 0 | none needed |
| Bus routes | 4,130 | Duplicates, missing names | 0 | none needed |
| Bus trips | 54,342 | Only 1-2 stops listed (incomplete stop list in the live-tracking feed) | 7,128 (13%) | kept in trip counts; excluded from length and stops-per-trip statistics |
| Stop times | 1,454,128 | Duplicates, broken references, missing times | 0 | none needed |
| Metro entries / exits | 92,280 / 95,616 | Duplicates, missing, negative counts | 0 | none needed |
| Metro OD | 1,273,629 | Entry and exit at the same station | 15,261 | excluded from the OD analysis |

A first version flagged 48 stops as outside Bengaluru; they were real BMTC stops (Magadi Road villages, Chikkaballapur), so the check was widened to the BMTC service area.

### Route distribution, high-use routes and shared stops

- **Typical route:** median 18.2 km, 30 stops per trip, 11 hours of service a day. Most routes run few trips (median 3 per weekday); a small core runs over 200.
- **Highest-frequency routes:** 375-D Kengeri to Banashankari (347 weekday trips), 378 Electronic City to Kengeri (316), 401-M Kengeri to Yeshwanthapura (306), 410-FA Banashankari to Yeshwanthapura (289).
- **Most shared stops:** Kempegowda Bus Station, Majestic (1,019 routes), Corporation (811), Town Hall (737), Maharani College (611), KR Circle (547), KR Market (526).

### Connectivity and access to metro

- Each stop is served by a median of 6 routes; 19% of stops have a single route.
- 1.53 million route pairs share at least one stop, so a typical route connects to 704 others with one transfer (network density 0.18).
- Only 5.0% of bus stops lie within 400 m of a metro station, and 11.1% within 800 m; the median stop is 5.7 km from the nearest station. This is the gap feeder buses must bridge.

### Bus operating speed

Scheduled BMTC speed has a median of 15.8 km/h across 46,816 weekday trips. It falls to 15.3 to 15.4 km/h in the 8-10 am and 5-7 pm peaks and rises to about 22.8 km/h at night. Montevideo's buses average 18 km/h (Nesmachnow et al. 2023). BMTC timetables are partly interpolated, so these figures describe the schedule, not measured traffic.

### Metro demand patterns

- Weekday ridership has two peaks: 8-10 am carries 26% of daily entries and 5-7 pm carries 27%. Weekends peak in the evening (24%).
- Busiest stations on pre-opening weekdays: Majestic (29,700 entries a day), Benniganahalli (26,600), Indiranagar (23,900), MG Road (21,100), Krishnarajapura (19,900).
- Busiest OD pair: Benniganahalli to Majestic (2,380 trips a day), then Kadugodi Tree Park and Sri Sathya Sai Hospital in both directions.

### Network growth

&#91;embedded content: notebook 09 · network\_over\_time.csv · 26 snapshots, Jan 2024 to Nov 2026\]

Stops rose from 8,089 to 10,128 and routes from 2,953 to 5,063 over the same period.

### Storage format: CSV (as proposed) vs Parquet on HDFS

| Measure (stop\_times, 1.45 M rows) | CSV | Parquet | Parquet advantage |
| --- | --- | --- | --- |
| Size on HDFS | 47.2 MB | 11.2 MB | 4.2x smaller |
| Count rows | 0.57 s | 0.17 s | 3.3x faster |
| Trips per stop (group by) | 1.18 s | 0.38 s | 3.1x faster |
| Read one column | 1.11 s | 0.29 s | 3.8x faster |

The proposal named CSV; the pipeline keeps the original CSV and GTFS text as the raw layer and stores the working copy as Parquet, because it is columnar and compressed.

## 6 Results

The pre-registered test finds no diversion away from bus-linked destinations; the clear effects are a frequency response on the Yellow Line and a bus supply response along it.

### 6.1 Exposure check: bus links are not just geography

YellowLink is almost uncorrelated with metro distance to RV Road (Spearman -0.03), so the bus score and plain metro geography can be told apart. It correlates 0.97 with YellowLinkDir and 0.98 with Collinear, and only 0.22 with total bus trips.

### 6.2 Main test (RQ1)

| Specification | Effect after opening | 95% CI | p |
| --- | --- | --- | --- |
| OLS, per 1 SD YellowLink (primary) | +0.65% | -2.1% to +3.4% | 0.64 |
| OLS, frozen 10 transfer stations | +0.24% | -7.5% to +8.0% | 0.95 |
| PPML, per 1 SD YellowLink | +0.92% | -1.8% to +3.6% | 0.50 |
| PPML, transfer stations | +0.89% | -6.2% to +8.0% | 0.81 |
| OLS, two-way clustered | +0.65% | -2.1% to +3.4% | 0.64 |
| OLS, YellowLinkDir | +0.64% | -2.3% to +3.6% | 0.67 |
| OLS, Collinear | -0.82% | -3.6% to +1.9% | 0.55 |
| Wild-cluster bootstrap (9,999 draws) | primary beta |  | 0.85 |
| Randomisation inference (1,000 shuffles) | primary beta |  | 0.39 |

The hypothesis predicted a negative effect. Every estimate is small, has the wrong sign or both, and none is significant. The confidence interval rules out a loss larger than about 2% per SD of bus-link score.

&#91;embedded content: notebook 02 · event\_study\_yellowlink.csv · 1-18 Aug 2025, 323,208 cells\]

Post-opening working days sit on zero. Dips of about 8% appear on weekends and the 15 Aug holiday both before and after the opening, so they reflect weekend travel patterns at these destinations, not the Yellow Line.

**Cross-origin check.** Origins that sent more trips to transfer stations before opening gained slightly less Yellow Line share afterwards (Spearman -0.30, p = 0.015; weighted slope -0.79, SE 0.63). This is the opposite of the bus-diversion prediction.

**Naive vs fixed effects.** A simple station before/after comparison of exits gives +1.49% per SD (SE 1.43, 67 stations). The fixed-effects model gives +0.65% (SE 1.38). Neither is significant; the fixed effects remove origin-level noise.

### 6.3 Time of day and September (RQ2)

- No band shows the predicted signature. Transfer stations: AM-peak entries -3.5% (p = 0.34), PM-peak entries -1.8% (p = 0.64), AM-peak exits +0.2% (p = 0.97).
- Per SD of YellowLink, all band effects lie between -1.1% and +2.5%, every p above 0.36.
- September: entries +1.3% per SD (p = 0.18), exits +0.1% (p = 0.92). Weekly estimates for weeks 1 to 5 lie between -0.5% and +1.2%, all p above 0.73.

### 6.4 Headway cut on 10 September (RQ3)

| Model | Effect on Yellow stations | p | Elasticity |
| --- | --- | --- | --- |
| Entries, difference-in-differences | +8.7% (0.084 log points) | < 0.0001 | 0.30 |
| Entries, with feeder-bus interaction | +11.4% base; feeder term -3.6% | < 0.001; 0.20 | n/a |
| Exits, difference-in-differences | +6.1% (0.059 log points) | < 0.0001 | 0.22 |
| Synthetic control (entries) | +5.9% mean gap; pre-period RMSPE 0.022 | n/a | 0.21 |

A 24% shorter wait brought 6 to 9% more riders, an elasticity of 0.21 to 0.30. Stations with new feeder buses did not respond more. The synthetic Yellow Line is built mainly from Mantri Square Sampige Road (weight 0.22), Challaghatta (0.18) and Mahalakshmi (0.14).

### 6.5 Bus supply response (RQ4)

- Between 4 Aug and 2 Sep 2025, routes added near Yellow stations include V-EXP 600F (44 trips/day), MF-22 (43), V-500SB (42), KIA-14A (24), and the feeders MF-22A to MF-22D. The MF-22 family adds about 103 weekday trips.
- Existing routes grew too: D19-ELC from 17 to 46 trips and 500-DJ from 34 to 54.
- Ten Yellow stations had more bus trips in September, including Central Silk Board, Electronic City, Bommanahalli and Hosa Road.
- Across 26 snapshots, supply near Yellow stations was flat until Nov 2025, then rose by about 1.6 log points (p of about 0.04 to 0.07) from Dec 2025. A jump this size likely reflects new routes entering live tracking as well as new service.
- Supply at the 10 transfer stations drifted down by about 0.3 log points over 2026 (p of about 0.08 to 0.14).

### 6.6 Population access (RQ6)

| Measure | People | Share of 10.13 M |
| --- | --- | --- |
| Within 800 m of a metro station before the Yellow Line | 1.72 M | 16.9% |
| Within 800 m after | 2.06 M | 20.3% |
| Gained direct access | 0.34 M | 3.4% |
| Within 400 m of a bus stop with a trip to the Yellow corridor | 4.92 M | 48.5% |
| Bus link only, no direct metro access | 3.73 M | 36.8% |

Direct gains sit in five constituencies: Bommanahalli (+130,000), Jayanagar (+89,000), B.T.M Layout (+59,000), Anekal (+37,000) and Bangalore South (+30,000). In B.T.M Layout 62% of people can reach the corridor only by bus.

The 2018 vs 2025 stop comparison matched 75 to 97% of 2018 stops, but trip counts fell 9 to 67% in every constituency. That uniform fall most likely reflects the different counting systems, so it is reported as indicative only.

## 6A Extensions: for whom, why not, and what next

The extensions find no group or trip type in which the first-week diversion appears, but they show a strong observational link between bus connections and ridership, and a first small sign of diversion after the September headway cut.

### 6A.1 Observational vs causal: the tension with prior studies

Across the 68 old stations before the opening, stations with stronger bus links to the Hosur Road corridor are much busier: +28.6% daily entries per SD of YellowLink (SE 10.1%, p = 0.005, R-squared 0.30, controlling for bus volume, population, line and distance to RV Road). This is the kind of association that observational Bengaluru studies report (Hasan et al. 2025; Gadepalli et al. 2022).

The causal test asks a different question: did those stations lose trips when the Yellow Line offered an alternative? They did not (+0.65% per SD, p = 0.64). Bus connectivity predicts where riders are, but in the short run it did not move them.

| Evidence | Design | Bus-link effect | p |
| --- | --- | --- | --- |
| Cross-station level (before opening) | Observational, 68 stations | +28.6% entries per SD | 0.005 |
| Change after opening (11-18 Aug) | Natural experiment, OD fixed effects | +0.65% trips per SD | 0.64 |
| Change after headway cut (10 Sep) | Station panel, 68 stations | -1.3% exits at transfer stations | 0.037 |

### 6A.2 Heterogeneity: for whom

| Origin characteristic (standardised) | Main effect per SD YellowLink | Interaction | p (interaction) |
| --- | --- | --- | --- |
| Job-centre index: log(AM exits / AM entries), pre-opening weekdays | +0.65% | -0.27% | 0.18 |
| Origin's own bus link to the corridor | +0.66% | +0.31% | 0.13 |
| Population within 800 m | +0.65% | -0.07% | 0.64 |

No origin type shows a diversion effect. The job-centre interaction has the expected sign (commuter origins slightly more responsive) but is not significant.

### 6A.3 Pair-level substitution: when is the Yellow Line a real alternative?

For each origin-destination pair, metro stops from the origin to RV Road were compared with stops to the current destination (from the BMRCL fare table). For 58% of pairs, RV Road is no farther than the destination, so switching to the Yellow Line costs no extra metro travel.

| Specification | Estimate | p |
| --- | --- | --- |
| Bus-linked destination x substitute pair (binary) | -2.5% | 0.24 |
| Bus-linked destination x extra stops via RV Road (per SD) | +0.24% | 0.64 |

The binary interaction points in the predicted direction (substitute pairs lose more), but the estimate is imprecise.

### 6A.4 Second shock: diversion as service improved

In September only station totals exist. After the 10 Sep headway cut, the 10 frozen transfer stations lost 1.3% of exits relative to other old stations (p = 0.037); per SD of YellowLink, exits fell 0.4% (p = 0.13), and entries did not change (p = 0.54 and 0.73). With 4 tests, one result at p = 0.037 is suggestive, not conclusive. It is consistent with diversion beginning only once the Yellow Line became frequent enough.

### 6A.5 Sensitivity: incomplete bus trips

Rebuilding the bus-link score without the 7,128 trips that list only 1-2 stops changes it little (correlation 0.948 with the original). The main estimate stays +0.61% per SD (p = 0.66).

### 6A.6 Feeder network maturity

| GTFS snapshot | Metro-feeder (MF) services | Weekday feeder trips | Metro stations within 400 m of a feeder stop |
| --- | --- | --- | --- |
| 5 Jan 2024 | 108 | 4,285 | 65 |
| 4 Aug 2025 (before Yellow) | 66 | 2,510 | 56 |
| 2 Sep 2025 (after Yellow) | 71 | 2,581 | 62 |
| 9 Nov 2026 (before Pink) | 129 | 3,111 | 70 |

Feeder coverage was at a low point when the Yellow Line opened and is much larger before the Pink Line, so the Pink Line test happens under a more mature feeder network. Route naming differs between snapshots, so service counts are indicative.

### 6A.7 Pink Line: second event, pre-registered

The Pink Line (Kalena Agrahara to Suddaguntepalya, 5 new stations plus the Jayadeva Hospital interchange) opened on 14 Nov 2026. Its bus-link scores were computed from the 9 Nov 2026 GTFS snapshot, and the top 10 stations were frozen at 17:59 UTC on 21 Nov 2026, before any Pink Line ridership is available.

- **Frozen list:** Ragigudda, Central Silk Board, Kundalahalli, Sri Sathya Sai Hospital, Nallurahalli, Lalbagh, Banashankari, Biocon Hebbagodi, Pattandur Agrahara, Huskur Road (SHA-256 9a434b7c...357b).
- **Primary test:** identical to the Yellow Line model, with zPinkLink of the destination.
- **Exposure check:** PinkLink correlates -0.34 with metro distance to Jayadeva Hospital, so it is not just geography.
- **Data needed:** station-pair hourly data for Nov-Dec 2026 by RTI (Appendix D).

If the Pink Line also shows no diversion, the null holds across two events and two stages of feeder maturity; if it does, it shows that integration conditions must mature first.

## 6B All lines: Purple, Green and Yellow

Across the whole network, the busiest stations are not the best connected by bus: Seetharampalya, MG Road, Kengeri, Vidhana Soudha and Majestic carry heavy metro demand with weak or no feeder links.

### 6B.1 Bus-metro integration index for every station

The index averages four standardised measures for each station: weekday bus trips and routes within 400 m (straight line), metro-feeder (MF) trips, and residents within 800 m. It is compared with September weekday ridership; a large positive gap means a busy station with weak bus links.

| Line | Stations | Mean integration index | Mean bus trips within 400 m | Mean feeder trips | Mean weekday entries (Sep) |
| --- | --- | --- | --- | --- | --- |
| Green | 30 | +0.17 | 1,890 | 61 | 8,984 |
| Purple | 36 | -0.03 | 1,977 | 89 | 11,226 |
| Yellow (new) | 15 | -0.33 | 1,951 | 24 | 3,549 |
| Majestic interchange | 1 | +0.73 | 14,385 | 0 | 32,976 |
| RV Road interchange | 1 | +0.13 | 1,052 | 78 | 9,034 |

| Busy but poorly connected (largest gap) | Line | Weekday entries | Bus trips within 400 m | Feeder trips |
| --- | --- | --- | --- | --- |
| Seetharampalya | Purple | 10,497 | 0 (nearest stop 404 m) | 0 |
| Mahatma Gandhi Road | Purple | 21,195 | 827 | 0 |
| Kengeri | Purple | 6,345 | 6 | 0 |
| Dr. B. R. Ambedkar (Vidhana Soudha) | Purple | 13,267 | 1,762 | 0 |
| Majestic | Interchange | 32,976 | 14,385 | 0 |
| Indiranagar | Purple | 24,286 | 928 | 310 |
| Sri Sathya Sai Hospital | Purple | 12,150 | 1,149 | 114 |
| Trinity | Purple | 14,901 | 790 | 0 |

Best integrated: Banashankari, Deepanjali Nagar, Jalahalli, Dasarahalli and Mysore Road, each with over 2,300 bus trips and 200-450 feeder trips a day. The new Yellow stations have as many buses nearby as old stations but few feeders (24 trips on average), which matches their slow ramp-up.

The walking network underestimated bus access at a few stations beside highways (Kengeri, Trinity), so this index uses straight-line distance. The main test was re-run with straight-line scores: +0.76% per SD (p = 0.60), still null.

### 6B.2 Demand by line

| Line | Weekday entries 1-10 Aug | 11-18 Aug | September | AM peak share (8-10) | PM peak share (17-19) |
| --- | --- | --- | --- | --- | --- |
| Purple | 398,917 | 418,724 | 404,148 | 26.4% | 29.3% |
| Green | 264,625 | 280,430 | 269,513 | 28.2% | 23.9% |
| Yellow | closed | 54,334 | 53,230 | 21.9% | 30.7% |
| Majestic | 30,288 | 36,722 | 32,976 | 20.0% | 22.1% |
| RV Road | 8,903 | 10,439 | 9,034 | 22.4% | 30.3% |

Green Line stations are morning-origin (residential: 28% of entries in the AM peak); Purple and Yellow are more evening-origin (job centres such as Whitefield and Electronic City). Yellow ridership held at about 53,000 a day in September, before the headway cut fully fed through.

### 6B.3 How the opening changed each line

| Trips starting on | Weekday trips before | After | Change | Share of trips going to Yellow, after |
| --- | --- | --- | --- | --- |
| Purple | 397,204 | 417,270 | +5.1% | 1.8% |
| Green | 263,277 | 278,841 | +5.9% | 5.4% |
| Majestic | 30,183 | 36,589 | +21.2% | 8.4% |
| RV Road | 8,838 | 10,640 | +20.4% | 22.8% |

Both old lines grew after the opening; Green feeds the Yellow Line three times as much as Purple (5.4% vs 1.8% of trips) because RV Road is on the Green Line. The bus-diversion test split by line stays null: Purple destinations -0.38% (p = 0.47), Green +2.7% (p = 0.48).

## 6C Fare revenue: the economic side

Weekday fare revenue rose 17.2% after the Yellow Line opened, from Rs 3.27 crore to Rs 3.83 crore a day, and the 10 September headway cut is worth about Rs 5.4 crore a year in extra fares. Figures come from BMRCL's own fare and revenue fields in the station-pair data (notebook 12).

| Measure (weekday average) | Before (1-10 Aug) | After (11-18 Aug) | Change |
| --- | --- | --- | --- |
| Trips | 699,503 | 796,124 | +13.8% |
| Fare revenue | Rs 3.27 crore | Rs 3.83 crore | +17.2% |
| Average fare | Rs 46.7 | Rs 48.1 | +2.9% |
| Revenue from trips not using the new stations | Rs 3.27 crore | Rs 3.37 crore | +3.1% |

- **Yellow Line trips** (to or from a new station) brought Rs 45.8 lakh a weekday, 12% of all fare revenue, at an average fare of Rs 56.8: they are longer than average trips.
- **Revenue grew faster than trips** (+17.2% vs +13.8%) because the new trips are long, higher-fare journeys.
- **The headway cut:** the causal entry effect (+8.7%, Section 6.4) applied to 48,414 Yellow weekday entries at Rs 51.4 average fare gives about Rs 2.2 lakh more per weekday, about Rs 5.4 crore over 250 weekdays a year.
- **Limits:** each period has only 5 weekdays; this is fare-box revenue, not profit, because the cost of running the extra train is not public; passengers' time savings, the main economic benefit of shorter waits, are not counted.

## 7 Model evaluation and comparative analysis

Spark MLlib predicts September ridership at old stations very well (Random Forest R-squared 0.96), but adding bus-network features improves test error by at most 1.6% and does not reliably beat shuffled bus features. This matches the econometric null.

### 7.1 Design

- **Task:** predict hourly entries at the 68 old stations after the Yellow Line opened.
- **Train:** 11-18 Aug 2025 with 3-fold cross-validation for tuning. **Test:** 1-30 Sep 2025, fully out of time (6 am dropped because the first train moved).
- **Targets:** `y_level` = log(1 + entries); `y_change` = log(1 + entries) minus the same station-hour's pre-opening average, i.e. the redistribution.
- **Models:** Linear Regression (elastic net; regParam 0, 0.01, 0.1; elasticNet 0, 0.5), Random Forest (100 trees; depth 8, 12), Gradient-Boosted Trees (60 iterations; depth 4, 6; step 0.1).
- **Feature sets:** metro only (hour, day of week, weekend, holiday, pre-opening level, hops to RV Road, line, location, population within 800 m); metro + bus (adds the 7 bus scores); metro + shuffled bus, the same 7 columns shuffled across stations.
- **Pipeline:** OneHotEncoder, VectorAssembler and the regressor inside a Spark Pipeline, tuned by CrossValidator (parallelism 4); data staged as Parquet.

The shuffled set is the key control. With 68 stations, any station-level number partly acts as a station ID, so bus data counts as informative only if it beats the shuffled version.

### 7.2 Results on the September test set

| Target | Model | RMSE metro only | RMSE + bus | RMSE + shuffled bus | R-squared + bus | Gain vs metro only | Gain vs shuffled |
| --- | --- | --- | --- | --- | --- | --- | --- |
| y\_level | Random Forest | 0.2646 | 0.2635 | 0.2660 | 0.964 | +0.4% | +0.9% |
| y\_level | GBT | 0.3073 | 0.3065 | 0.3102 | 0.952 | +0.3% | +1.2% |
| y\_level | Linear Regression | 0.5795 | 0.5707 | 0.5800 | 0.832 | +1.5% | +1.6% |
| y\_change | Random Forest | 0.2711 | 0.2723 | 0.2719 | 0.526 | -0.4% | -0.2% |
| y\_change | GBT | 0.3172 | 0.3149 | 0.3056 | 0.366 | +0.7% | -3.0% |
| y\_change | Linear Regression | 0.3769 | 0.3765 | 0.3782 | 0.094 | +0.1% | +0.4% |

RMSE is in log points; gain = 1 - RMSE(+bus) / RMSE(comparison).

### 7.3 What the comparison shows

- **Model ranking:** Random Forest is best on both targets, then GBT, then Linear Regression. On the passenger scale, Random Forest misses by 163 entries per station-hour (RMSE) and 84 (MAE), against 765 and 214 for Linear Regression.
- **Bus features:** small gains for ridership levels (0.3 to 1.6%), and no gain for redistribution. For GBT on `y_change`, shuffled bus data does 3% better than real bus data, a sign that the trees use the columns as station identifiers.
- **Feature importance:** the pre-opening level of the same station-hour dominates (GBT importance 0.67 for `y_level`). For `y_change` the leading features are the pre-opening level (0.12), population within 800 m (0.07) and location. The best bus feature, BusRoutes, has importance 0.02.
- **Overfitting:** tree models fit training days better than September (Random Forest `y_change` R-squared 0.83 train vs 0.53 test), so redistribution is only partly predictable from station traits.

### 7.4 Simple vs proper models (rubric comparison)

| Question | Simple approach | Proper approach | Lesson |
| --- | --- | --- | --- |
| Did bus-linked stations lose riders? | Station before/after % change: +1.49% per SD | OD model with origin-date and pair fixed effects: +0.65% | Both null; fixed effects remove origin noise and give a valid standard error |
| Is the p-value trustworthy with 68 clusters? | Clustered SE: p = 0.64 | Wild bootstrap p = 0.85; randomisation p = 0.39 | Conclusion unchanged |
| Do bus features help prediction? | Compare with metro only: up to +1.5% | Compare with shuffled bus: -3.0% to +1.6% | A placebo is needed to avoid over-claiming |
| Headway effect | Raw before/after | DiD +8.7% and synthetic control +5.9% | Two designs bracket the elasticity at 0.21 to 0.30 |

### 7.5 Tuning grid note

These results come from notebook 05b, a smaller grid run because the full grid (up to 300 trees and 200 boosting rounds, notebook 05) was still running after 4 hours. Both use identical data, splits, features and folds, and every feature set gets the same grid, so the comparison between feature sets is fair. Notebook 05 later finished (about 3.5 hours of model fitting, mostly GBT). The larger grid confirms every conclusion:

| Target | Model | Gain vs metro only, full grid | Gain vs shuffled, full grid | Test R-squared + bus, full grid |
| --- | --- | --- | --- | --- |
| y\_level | Random Forest | -1.2% | +0.1% | 0.963 |
| y\_level | GBT | +0.5% | +1.0% | 0.951 |
| y\_level | Linear Regression | +1.5% | +1.6% | 0.832 |
| y\_change | Random Forest | -1.0% | +0.3% | 0.539 |
| y\_change | GBT | -0.2% | 0.0% | 0.386 |
| y\_change | Linear Regression | +0.1% | +0.4% | 0.094 |

Random Forest stays the best model, test R-squared moves by at most 0.02, and bus features again change error by between -1.2% and +1.6%. The tuning grid does not drive the result.

### 7.6 The planning question: stations with no ridership history

The tests above predict old stations, where last week's ridership at the same hour explains almost everything, leaving bus data nothing to add. A planner's question is different: how busy will a station be when it has no history? Two Spark MLlib tests answer it, with hour-of-day bus trips added as a feature (bus departures within 400 m in the same hour).

| Test | Features | Best model | Hourly R-squared (log) | Daily error (MAPE) | Rank correlation of station totals |
| --- | --- | --- | --- | --- | --- |
| 68 old stations, 5-fold leave-stations-out | metro only | Random Forest | 0.378 | 42.9% | 0.56 |
|  | metro + bus | Random Forest | 0.357 | 43.8% | **0.60** |
|  | metro + shuffled bus | Random Forest | 0.286 | 47.6% | 0.50 |
| 15 new Yellow stations, trained on old | metro only | Random Forest | negative | 216% | 0.26 |
|  | metro + bus | Random Forest | negative | 236% | **0.60** |
|  | metro + shuffled bus | Random Forest | negative | 219% | 0.35 |

Values from the Kaggle run of notebook 10.

- **Levels:** no feature set predicts how many riders an unseen station gets better than metro-only features (R-squared about 0.36-0.38). For the new Yellow stations every model over-predicts by about 2x, because a new line at a 25-minute headway is still ramping up; a model trained on mature stations cannot know that.
- **Ranking, where bus data helps:** with real bus features, Random Forest ranks the 15 new Yellow stations by busyness with rank correlation 0.60, against 0.26 with metro-only and 0.35 with shuffled bus features. On unseen old stations the gain is smaller (0.60 vs 0.56 metro-only and 0.50 shuffled). Bus connectivity tells a planner which new stations will be busiest, even when it cannot say how busy.
- **Caution:** 15 test stations is a small sample, so the ranking gain is indicative, and Random Forest results vary slightly between runs (a local run gave 0.61 vs 0.35). GBT gains over metro-only (0.49 vs 0.20) but not over its placebo (0.53), so only the Random Forest result passes the placebo check.

## 7A A useful model: next-day metro demand forecaster

The final forecaster (Spark MLlib Random Forest) predicts tomorrow's entries at every station and hour with an average miss 8.1% smaller than the best simple guess, gives 90% ranges that hold 93% of the time, and warns of crowded hours with 86% precision. Figures are from the Kaggle run of notebook 11.

### 7A.1 What it is for

BMRCL plans trains and staff the day before. The forecaster gives, for each of 83 stations and each hour from 6 am to 10 pm: a forecast of entries, a range it is 90% sure about, and a crowding warning when entries are expected above 1,637 an hour (the busiest 5% of station-hours). Unusual hours are flagged for a person to check.

### 7A.2 Design

- **Data:** September 2025 station-hourly entries, the only continuous month available (30 days, 83 stations).
- **Learn** on 8-17 Sep, **calibrate ranges** on 18-21 Sep, **test once** on 22-30 Sep: 12,699 station-hours never seen, including Navaratri week, a hard test.
- **Inputs:** the same hour yesterday and last week, the 7-day mean, yesterday's daily total; hour, weekday, weekend, holiday; station location, population, new-line flag; bus trips, routes and feeder trips nearby.
- **Simple guesses to beat:** "same hour yesterday" and "same hour last week". Last week is far stronger, because weekday rhythms repeat.
- **Ranges:** split-conformal, from calibration-day errors in three busyness groups.
- **Confidence:** 1,000 bootstrap resamples of test days.

### 7A.3 Version log

| Version | Model | Average miss (entries/station-hour) | vs "same hour last week" | 95% range |
| --- | --- | --- | --- | --- |
| Simple | Same hour yesterday | 125.4 | -100.1% | -231.5 to -8.5 |
| Simple | **Same hour last week** | **62.7** | 0 (reference) |  |
| V1 | GBT, learns the level | 68.4 | -9.1% | -27.9 to +2.6 |
| **V1 (final)** | **Random Forest, learns the level** | **57.6** | **+8.1%** | **-0.5 to +14.2** |
| V2 | GBT, learns the change from last week | 68.5 | -9.3% | -31.9 to +2.9 |
| V2 | Random Forest, learns the change from last week | 74.7 | -19.2% | -58.4 to -1.8 |
| V3 | Random Forest + hourly weather (rain, temperature) | 57.0 | +9.1% | -0.8 to +16.4 |
| V3 | GBT + hourly weather | 69.8 | -11.4% | -32.3 to +0.4 |

V2 was meant to refine the strong last-week guess, but it did worse: the test week was Navaratri, so last week's pattern was a poor anchor. V1 Random Forest is the final model. Its RMSE (106.2) is 10.4% below last week's (118.5), so it makes fewer large misses. The 95% range for the average-miss gain just crosses zero, so the gain is modest and not fully certain on nine test days.

### 7A.4 What each input is worth

| Input group | Skill points added | 95% range | Reliable? |
| --- | --- | --- | --- |
| Calendar (weekday, weekend, holiday) | +4.6 | -1.5 to +13.2 | not quite |
| Weather (V3 vs V1) | +1.0 | -2.5 to +4.1 | no |
| Station traits | -0.3 | -1.1 to +0.7 | no |
| Bus network | -0.5 | -0.8 to 0.0 | no |

V3 adds hourly Bengaluru rain and temperature from the Open-Meteo archive, used as observed (as if tomorrow's weather forecast were exact). Its gain over V1 is within noise, so the simpler V1 stays final. A festival flag could not be learned: Navaratri falls only in the test week.

For day-ahead forecasting, recent ridership and the calendar carry the signal; bus connectivity adds nothing, matching every other test in this report.

### 7A.5 Ranges, warnings and anomalies

| 90% range check | Quiet stations | Medium | Busy | All |
| --- | --- | --- | --- | --- |
| Share of actual values inside the range | 91.6% | 93.8% | 94.3% | **93.2%** |

| Crowding warning (above 1,637 entries/hour) | Warnings issued | False alarms | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- |
| **Forecaster** | 565 | 80 | **85.8%** | 86.1% | **0.860** |
| Same hour last week | 631 | 124 | 80.3% | 90.1% | 0.849 |
| Same hour yesterday | 538 | 140 | 74.0% | 70.7% | 0.723 |

Of 563 truly crowded station-hours, the forecaster catches 86% and raises 44 fewer false alarms than the last-week guess (80 vs 124), at the cost of missing 22 more crowded hours. 312 test hours fell well outside the range. The largest were the early-morning hours of Sunday 28 Sep, quiet across many stations at once, and evening spikes at Madavara on 27-28 Sep (3,076 and 2,814 entries at 5 pm against about 550 forecast), most likely crowds leaving events at the exhibition centre beside the station.

### 7A.6 Station types (clustering)

Spark MLlib KMeans on each station's weekday hourly rhythm found two types (silhouette 0.71 at k = 2, falling to 0.32 at k = 8): 42 **morning-origin** stations, where most entries happen in the morning peak (residential areas), and 41 **evening-origin** stations, where entries peak in the evening (job centres such as Electronic City, Hoodi and Kundalahalli near ITPL, and the CBD stations MG Road, Cubbon Park and Vidhana Soudha; line ends such as Whitefield (Kadugodi) and Kengeri are morning-origin). This split, found without location data, matches the planning distinction between home-end and work-end stations.

## 7B Interactive layer: dashboard and web demo

Every result in this report can be explored in two interactive tools that read the pipeline's output files directly.

| Tool | What it is | How to open | Pages |
| --- | --- | --- | --- |
| Streamlit + Plotly dashboard (`dashboard/app.py`) | Multi-page analytics app reading the Kaggle output tables | `pip install streamlit plotly`, then `streamlit run dashboard/app.py` | Overview, how it works (plain-language tour), line explorer (Purple, Green, Yellow, Pink), network analytics, station explorer (map), Yellow Line test, headway calculator, all lines, machine learning, demand forecaster, Spark scaling, Pink Line, data and reproducibility |
| Yellow Line Explorer (web page) | Single-page demo for the viva, no install | Open the shared link in a browser | Station map with bus links and hourly ridership, rerun the test under 22 specifications, headway calculator, under-served stations, Pink Line pre-registration |

The dashboard has light and dark themes (same palettes as the reference atlas) that the charts and cards follow. All 13 dashboard pages were tested automatically (Streamlit AppTest) and load without errors. Charts and tables come from pipeline outputs; nothing is typed in by hand.

## 8 Scalability

Spark overtakes pandas once the job reaches a few snapshots, and with 4 cores it finishes the full 26-snapshot job in 22.5 s against 50.3 s.

&#91;embedded content: notebook 06 · scaling\_results.csv · Kaggle 4 vCPU\]

The benchmark job reads stop\_times, trips and stops, filters weekday service, joins and counts trips per stop. It runs on 1, 5, 10, 20 and 26 snapshots, with Spark on 1, 2 and 4 cores and pandas on one core.

- **Small data favours pandas:** on 1 snapshot (2.2 M rows) pandas takes 4.8 s against 5.8 s for Spark on 1 core, because Spark pays a fixed start-up and planning cost.
- **Speedup with cores:** 4 cores are 1.8 to 2.0x faster than 1 core, not 4x. Kaggle's 4 vCPUs are likely 2 physical cores with hyper-threading, and the job is partly limited by reading files.
- **Linear growth:** Spark time grows roughly in line with rows. Pandas grows faster and holds all data in memory (peak about 0.7 GB here). It would run out of memory long before Spark on a city-wide multi-year feed.
- **Partition pruning:** because snapshots are stored as `snapshot=<date>` folders, Spark reads only the snapshots a query asks for.

## 9 Robustness, threats to validity and limitations

The null result survives 22 alternative specifications; the two that reach p < 0.05 point the opposite way to the hypothesis.

&#91;embedded content: notebook 07 · robustness.csv · 22 specifications\]

With 22 tests, about one false positive at the 5% level is expected by chance. The significant placebo on 5 Aug does warn that day-of-week differences between destinations are not fully absorbed, which the weekend dips in the event study also show. The weekdays-only version stays null (p = 0.77).

### 9.1 Threats to validity and how each was handled

| Threat | Why it matters | How it was handled | Remaining risk |
| --- | --- | --- | --- |
| Short pre-period (10 days, 6 clean weekdays) | Parallel trends hard to test | Daily event study; placebo dates; randomisation inference | Moderate: weekend pattern differs by destination |
| Bus score = metro geography | Could not separate bus from location | Correlation with hops to RV Road is -0.03; controls for hops, line, bus volume | Low |
| Specification search | Many variants could find a spurious result | One primary model frozen and hashed before ridership was opened | Low; Kaggle timestamp, not OSF |
| Local events (Lalbagh flower show 7-18 Aug, I-Day, festival 8 Aug, joyriders) | Shocks concentrated near high-exposure stations | Dropped each in turn | Low |
| Few clusters (68) | Clustered SEs can be too small | Wild-cluster bootstrap and randomisation inference | Low |
| Ramp-up of a new line | Could inflate the headway effect | Synthetic control; 6 am dropped | Moderate: part of the 0.30 elasticity may be ramp-up |
| GTFS covers only tracked routes | Supply changes can be coverage changes | Results checked against named routes (MF-22) | Moderate for the Dec 2025 jump |
| Exposure measures supply, not bus use | No BMTC ticket data | Stated as a limitation | Cannot be fixed with open data |

### 9.2 Limitations

- **No OD data after 18 Aug.** September has only station totals, so the diversion test covers the first 8 days. Longer-run diversion could still exist.
- **No bus ridership.** The study measures bus links, not bus trips. BMTC electronic ticket counts by route would show the mechanism directly.
- **Single city, single event.** The Pink Line opening (14 Nov 2026) offers a replication that this study could not yet include.
- **Voters, not residents.** Booth population counts adults on the 2022 rolls.
- **Reduced ML grid.** The headline ML results use the smaller grid (Section 7.5).
- **Hardware.** Kaggle's 4 vCPUs limit the scaling curve to 4 cores; a multi-node cluster was not available.

## 10 Discussion, policy implications and publishability

In its first weeks the Yellow Line grew by attracting new trips and responding to frequency, not by pulling riders away from metro-plus-bus routes.

### 10.1 Interpreting the null

- **Likely explanations:** commuters who used metro plus bus to reach Electronic City may not switch within 8 days; at a 25-minute headway the Yellow Line was slower than the existing bus leg for many trips; and many Yellow riders were new to the metro (people living on Hosur Road) rather than diverted Green and Purple riders.
- **Supporting evidence:** frequency mattered (elasticity 0.21 to 0.30), and 3.73 M people can reach the corridor only by bus. Capacity, not the bus network, appears to have been the binding constraint in August.
- **What the null rules out:** a loss of more than about 2% per SD of bus-link score at bus-linked destinations in the first 8 days.

**The scientific statement.** Observational studies of Bengaluru find that bus feeders and parallel routes shape metro ridership (Hasan et al. 2025 model one month of data without fares; Gadepalli et al. 2022 compare yearly snapshots). Our data reproduce that association: bus-linked stations carry 29% more riders per SD. After an exogenous shock, however, the same bus links produced no measurable diversion in the first week, and only a small, borderline effect once frequency rose in September. The gap between the two is most plausibly time scale and adjustment cost: transfer habits, passes and routines do not change within days, and a 25-minute headway did not beat an existing metro-plus-bus routine. Cross-sectional associations therefore describe a long-run equilibrium; they should not be read as the short-run response planners can expect when a new line opens.

### 10.2 Policy implications

1. **Frequency first.** With an elasticity near 0.3, the fifth train (15-minute peak, 1 Nov 2025) should add roughly 7 to 8% more riders; each later train is a measurable gain.
2. **Feeders where the gaps are.** In B.T.M Layout, Bommanahalli and Bangalore South over half of residents can reach the corridor only by bus. MF-22-style feeders should be planned against such access maps.
3. **Joint data.** BMTC route ticket counts released alongside BMRCL ridership would let agencies see transfers directly.
4. **Pre-register evaluations.** Freezing an exposure list before looking at outcomes is cheap and makes later claims credible.

### 10.3 Publishability

The study's value lies in the design: a pre-registered, OD-level test with a clean null and a positive frequency elasticity, all on open data. The estimates below are the team's rough judgement, revised down from the pre-result review because the main result is null.

| Venue type | Example | Fit | Rough odds |
| --- | --- | --- | --- |
| Short paper, accepts null results | Findings (transport) | Short natural-experiment notes, pre-registration valued | About 30-40% |
| Regional transport journal | Case Studies on Transport Policy | Published Gadepalli 2022 on Bengaluru | About 20-30% |
| Conference, Big Data or ITS track | IEEE or Springer Scopus-indexed | Pipeline and scaling angle | About 55-65% |
| Top transport journal | Transportation Research Part A | Would need the Pink Line replication and BMTC ticket data | Under 5% now |

Strengthening steps: add the Pink Line opening as a second event, request July 2025 and Oct 2025 OD data by RTI for a longer window, and obtain BMTC ticket counts.

### 10.4 Comparison with published metrics

| Metric | This study (Bengaluru) | Published value | Source |
| --- | --- | --- | --- |
| Ridership elasticity to service frequency | 0.30 (entries, DiD); 0.21 (synthetic control) | Mostly +0.28 to +0.6 (headway changes, Massachusetts case studies); headway elasticity -0.26 to -0.28 (Chicago) | [KonSULT, Univ. of Leeds](https://www.its.leeds.ac.uk/projects/konsult/private/level2/instruments/instrument042/l2_042c.htm); [TRR 2350](https://journals.sagepub.com/doi/full/10.3141/2350-08) |
| Average bus operating speed | 15.8 km/h scheduled (15.3 peak) | 18 km/h, Montevideo | Nesmachnow et al. 2023 |
| Bus feeders and metro ridership | +28.6% entries per SD of bus link (cross-section, 68 stations); no short-run causal effect | Feeder services raise metro ridership (40 stations, 2 corridors, log-linear model) | [Hasan et al. 2025, TR-A 200](https://econpapers.repec.org/RePEc:eee:transa:v:200:y:2025:i:c:s0965856425002666) |
| Share of trips shifting to a new line | 5.4% of Green and 1.8% of Purple trips went to Yellow in week 1 | Existing stations lose flow after a new line opens (Nanjing Line 4) | Fu et al. 2018 |
| Spark speed-up | 2.2x vs pandas at 38.6 M rows (4 cores) | 15-25% travel-time savings from Spark/Hadoop traffic systems (different metric) | Miftah et al. 2025 |

Our frequency elasticity sits inside the published range, which supports the headway result. Bengaluru's scheduled bus speed is about 12% below Montevideo's. We reproduce the observational feeder association reported for Bengaluru, and add the causal finding that it does not translate into short-run diversion. Published station-level prediction accuracies were not available in comparable form, so Section 7.6 compares against our own metro-only and placebo baselines.

## 11 Conclusion and future work

Combining BMRCL metro and BMTC bus data around the Yellow Line opening, this study finds no bus-mediated diversion of metro trips in the first eight days (p = 0.64, bootstrap p = 0.85), a frequency elasticity of 0.21 to 0.30, and a visible bus feeder response.

| Research question | Answer |
| --- | --- |
| RQ1 Diversion from bus-linked stations | No; +0.65% per SD, CI rules out losses over about 2% |
| RQ2 Time-of-day signature and September | No signature; no delayed effect in any September week |
| RQ3 Headway elasticity | 0.30 (entries), 0.22 (exits), 0.21 (synthetic control) |
| RQ4 Bus supply response | MF-22 feeder family (about 100 trips a day) and express routes added; large tracked-supply rise from Dec 2025 |
| RQ5 Bus features in MLlib | At most 1.6% lower error; no reliable gain over a shuffled placebo |
| RQ6 Population access | +345,000 within 800 m; 4.92 M reach the corridor by bus |
| RQ7 Spark scaling | 2.2x faster than pandas at 38.6 M rows with 4 cores; pandas faster on one snapshot |

| Further question | Answer |
| --- | --- |
| Bus links vs ridership across stations (observational) | +28.6% entries per SD (p = 0.005): bus links predict where riders are, but did not move them |
| Diversion as service improved (10 Sep cut) | Transfer stations -1.3% exits (p = 0.037): a first, borderline sign |
| For whom / which trips | No origin type or substitute pair responds significantly |
| All lines | Busiest weakly connected stations: Seetharampalya, MG Road, Kengeri, Vidhana Soudha, Majestic (no feeder trips); Green riders took up Yellow 3x more than Purple riders |
| Predicting stations with no history | Bus data improves the ranking of the 15 new Yellow stations (rank correlation 0.26 to 0.60, placebo 0.35), not the level |
| Second event | Pink Line list frozen and hashed before any ridership exists |
| Proposal scope (network analytics) | 4,130 routes, 9,309 stops; Majestic hub (1,019 routes); 5% of stops within 400 m of metro; bus network +42% trips since 2024; Parquet 4.2x smaller than CSV |

| Tools delivered | Answer |
| --- | --- |
| Next-day demand forecaster | Average miss 8.1% smaller than "same hour last week"; 90% ranges hold 93.2%; crowding warnings 85.8% precision, 44 fewer false alarms |
| Station types | Two types by daily rhythm (silhouette 0.71): 42 morning-origin, 41 evening-origin |
| Interactive layer | Streamlit + Plotly dashboard (14 pages, including Fare revenue) and the Yellow Line Explorer web demo, both reading pipeline outputs |
| Reproducibility | 14 Kaggle notebooks (00-12 + 05b), all completed; code public on GitHub; OpenCity ridership verified identical to the data used |

**Future work.**

- Replicate on the Pink Line opening (14 Nov 2026) with the same frozen-list design.
- Extend the OD window by RTI to July and October 2025.
- Add BMTC ticket counts per route to observe transfers directly.
- Run the pipeline on a multi-node cluster to extend the scaling curve beyond 4 cores.

## Appendix A: Rubric mapping

| Rubric component (marks) | Where it is covered |
| --- | --- |
| Problem definition and literature survey (6) | Sections 1 and 2: natural experiment, 7 research questions, literature table and gap |
| Big Data technology and methodology (8) | Sections 3, 4 and 5: 8 datasets, HDFS + Spark 4 + MLlib architecture, 9-step method, pre-registration |
| Model evaluation and comparative analysis (6) | Sections 6 to 9: 3 MLlib models x 3 feature sets x 2 targets with a placebo, new-station prediction, the demand forecaster scored against simple baselines with a version log and bootstrap ranges, simple vs proper models, scaling, 22 robustness checks, comparison with published metrics (10.4) |
| Presentation and viva (10) | Figures 1 to 19 in the notebooks, the charts in this report, the Streamlit dashboard and Yellow Line Explorer for a live demo (Section 7B), and the threats table in Section 9 for likely questions |

## Appendix B: Notebook map and reproducibility

| Notebook | Purpose | Key outputs | Run time on Kaggle |
| --- | --- | --- | --- |
| 00 setup and data | Download all data, start HDFS, ingest 26 GTFS snapshots, build walk graph | HDFS tables, data checks | About 15 min |
| 01 bus-link score | Scores for 2 snapshots x 3 radius settings; freeze top 10 | frozen\_transfer\_stations.json, preregistration.md, fig 1 | About 10 min |
| 02 diversion test | OD panel in Spark SQL; main estimates; bootstrap; randomisation; event study | main\_diversion\_estimates.csv, figs 2-3 | About 20 min |
| 03 time of day, September, headway | Band models, weekly persistence, headway DiD and synthetic control | headway\_did.csv, figs 4-5 | About 15 min |
| 04 bus supply | Supply panel over 26 snapshots, route diff | route\_diff\_yellow.csv, figs 6-7 | About 20 min |
| 05 / 05b MLlib | Model x feature set x target comparison | mllib\_metrics.csv, mllib\_gain.csv, fig 8 | 05b about 30 min; 05 about 4.5 h |
| 06 scaling | Spark 1/2/4 cores x 1-26 snapshots vs pandas | scaling\_results.csv, fig 9 | About 40 min |
| 07 robustness | 22 specifications | robustness.csv, fig 10 | About 20 min |
| 08 population and wards | Booth access, constituency summaries, 2018 vs 2025 | access\_summary.csv, figs 11-12 | About 15 min |

**Notebook 09, network analytics** (about 20 min): data quality, route distribution, shared stops, connectivity, metro demand patterns, network over time and CSV vs Parquet; outputs `network_*.csv`, `metro_demand_*.csv` and figures 13-17. It reloads HDFS from notebook 00's files at the start, because each Kaggle session begins with an empty HDFS.

**Notebook 10, extensions and all lines** (about 15 min): Pink Line pre-registration, feeder maturity, heterogeneity, pair substitution, observational vs causal, second shock, sensitivity, bus speeds, integration index, line demand, new-station MLlib tests; figure 18.

**Notebook 11, demand forecaster** (about 15 min): next-day station-hour forecasts with Spark MLlib, version log, ablation with bootstrap ranges, conformal 90% ranges, crowding warnings, anomalies and KMeans station types; figure 19.

**Dashboard:** `streamlit run dashboard/app.py` reads `kaggle_results_acc2/` (the downloaded Kaggle outputs).

**Notebook 12, fare revenue** (about 2 min): weekday fare revenue before and after the opening, by line and fare slab, Yellow Line revenue, and the revenue value of the headway cut; figure 20. Code and results are also on GitHub: https://github.com/Yaswanth-Gullapudi/-bengaluru-transit-bda

**To reproduce:** upload the `t15-code` and `t15-ward` folders as Kaggle datasets, run notebook 00 with internet on, then attach its output to notebooks 01-08 and run them. All randomness uses seed 15. Code: `code/t15/` (config, env, data, bus, panels, econ, ml, scaling, wards, pipeline).

## Appendix C: Team roles

| Member | Main responsibilities |
| --- | --- |
| Gullapudi Yaswanth | Pipeline, HDFS/Spark setup, diversion test, report |
| Madhurashree M | Literature survey, bus-link score, bus supply analysis, figures |
| Mahadhii Ganapathi Subramanian | MLlib comparison, scaling benchmark, population access, slides |

Roles are a proposed split; edit to match what each member did.

## References

1. Hasan, Nirmale, Deepa and Pinjari (2025). Metro and bus competition and complementarity in Bengaluru. Transportation Research Part A 200, 104638.
2. Deepa, L., Pinjari, A. R., Nirmale, S. K., Srinivasan, K. K. and Rambha, T. (2022). A direct demand model for bus transit ridership in Bengaluru, India. Transportation Research Part A 163, 126-147. doi:10.1016/j.tra.2022.07.004
3. Gadepalli, Gumireddy, Bhamidipati and Cats (2022). BMTC performance with metro expansion. Case Studies on Transport Policy 10, 940-947.
4. Chai, Sun and Yin (2025). Navigating the impact of metro network on bus ridership. Transportation Research Part A 199.
5. Liu, Jin, Zhang, Gao et al. (2026). Transportation Research Part A 212, 105182.
6. Lu, Zhang, Ong, Kwan and Xie (2026). Journal of Planning Education and Research 46(1), 72-87.
7. Ding et al. (2025). Journal of Transport Geography 125, 104205.
8. Ding, F., Liang, Y., Wang, Y., Tang, Y., Zhou, Y. and Zhao, Z. (2024). A graph deep learning model for station ridership prediction in expanding metro networks (Metro-MGAT). UrbanAI'24, ACM SIGSPATIAL. doi:10.1145/3681780.3697247
9. Park, M. S., Eom, J. K., Heo, T.-Y. and Song, J. (2016). Intervention analysis of the impact of opening a new railway line on passenger ridership in Seoul. KSCE Journal of Civil Engineering 20, 2524-2534. doi:10.1007/s12205-015-1190-6
10. Fu et al. (2018). Journal of Advanced Transportation, Nanjing Line 4.
11. Lim (2025). MIT thesis on GTFS competing and complementary routes in direct-demand models.
12. Kori, V. and Srikanth, S. (2025). Evaluating the sustainability of metro and feeder bus integration: a Bengaluru Metro case study in India. Periodica Polytechnica Transportation Engineering 53(4), 462-471.
13. CiSTUP-BMTC research booklet (2023). Indian Institute of Science.
14. IISc (2026). Yellow Line commuter study, final project report.
15. CSTEP. Impact of metro on bus ridership in Bengaluru.
16. Accessibility effects of a new metro line, Oslo Fornebu. Findings.
17. Brussels Metro 3 accessibility, arXiv 2509.22223.
18. Wang et al. (2021); Brands et al. (2020), EJTIR; Gao et al. (2022).
19. Diagram Chasing (2025). Bengaluru Yellow Line station ridership analysis (blog).
20. Data: Vonter/bmrcl-ridership-hourly; Vonter/bmtc-gtfs; bmtc.vonter.top; OpenCity BMTC stops and routes by ward; OpenStreetMap contributors.

Items 2, 8, 9 and 12 were checked against publisher and index records on 22 Nov 2026.

## Appendix D: Data requests to extend the study

These drafts request the data that would turn the extensions into full tests. Edit names and addresses before sending.

**1. RTI to BMRCL (Public Information Officer, BMRCL, Shanthinagar, Bengaluru 560027)**

Under the Right to Information Act 2005, please provide in CSV or XLSX format:

1. Hourly station-to-station (origin-destination) ridership counts for all stations, 1 July to 10 August 2025 and 19 August to 31 October 2025.
2. The same data for 1 October to 31 December 2026, covering the Pink Line opening on 14 November 2026.
3. Hourly entries and exits by station for the same periods.

The data will be used for academic research on how new metro lines change travel patterns. Personal data is not requested.

**2. Data request to BMTC (Chief Traffic Manager, Planning) or CiSTUP, IISc**

We request daily ticket counts from electronic ticketing machines (ETM), aggregated by route and boarding stop, for July to October 2025, for routes serving the Hosur Road corridor (Silk Board to Electronic City and Bommasandra) and routes serving the metro stations Banashankari, Chickpete, Jayanagar, Lalbagh, South End Circle, Indiranagar and Krishnarajapura. Daily summaries for about 100 routes are enough. Aggregated counts contain no personal data.

**Expected gain.** Item 1 extends the main test from 8 days to about 11 weeks and allows the 10 Sep headway cut to be tested at OD level. Item 2 changes the bus side from supply (timetables) to use (tickets), observing the transfer mechanism directly.
