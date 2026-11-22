# Team 15: Publishable research directions combining BMTC bus and BMRCL metro data

*Prepared 2026-11-21 by the transit-research-scout agent. About 45 web searches. Abstracts or full text were read for the closest papers. Every reference in Section 8 was opened or confirmed through its publisher or index page. Anything not confirmed is marked **[unverified]**.*

---

## 0. TL;DR

1. **Your August 2025 metro data contains a natural experiment.** The BMRCL RTI data covers **1–18 Aug 2025** (hourly, by station and by station pair), plus **1–30 Sep 2025** (hourly, by station). The **Yellow Line (RV Road–Bommasandra, 16 stations, 19.15 km)** was inaugurated on **10 Aug 2025** and started commercial service on **11 Aug 2025**. A second shock follows on **10 Sep 2025**: a 4th train cut Yellow Line headway from **25 to 19 min**.
2. **Bus network snapshots from just before and just after the opening exist.** The community BMTC GTFS (Vonter/bmtc-gtfs, ODbL) was rebuilt on **2025-08-04** (pre-opening) and **2025-09-02** (post-opening). Monthly snapshots continue up to Nov 2026. You can therefore measure the bus-side supply response (new feeder routes MF-22 etc., relocated stops) alongside the metro-side demand response.
3. **Closest prior work and the gap.** Hasan et al. (2025, *TR Part A*) already model Bengaluru metro station ridership with metro–bus competition and complementarity terms. Their model is **cross-sectional**: 40 stations, 2 lines, before the Yellow Line. Gadepalli et al. (2022, *Case Studies on Transport Policy*) did a descriptive before/after study of the first metro lines' impact on BMTC. **Nobody has used the Yellow Line opening, or any Indian line opening, as a quasi-experiment, or tested whether bus-network exposure explains which existing metro stations gained or lost riders.** The only analysis of this data is a blog (Diagram Chasing): a naive per-station before/after at p<0.09, with no bus data.
4. **Recommendation: Idea A.** Use a difference-in-differences / event-study design with a continuous **bus-network exposure** treatment. Ideas B and C are strong companion or backup papers.

| Rank | Idea | Headline result | Novelty | Feasibility | Spark use |
|---|---|---|---|---|---|
| **1** | **A. Yellow Line natural experiment: does bus-network exposure explain who won and lost?** | Causal elasticity of station and OD ridership to the new line, moderated by GTFS bus overlap | High (first quasi-experiment on an Indian metro opening using bus+metro) | High (all data open, small) | Medium (GTFS×OD joins, 20+ GTFS snapshots, hourly panel) |
| 2 | B. Bus–metro feeder/competition index and new-line transfer test (Yellow out-of-sample, Pink Line Nov 2026 forecast) | Index that predicts station ridership; ranked feeder-gap list; tested on unseen stations | Medium-high | High | Medium |
| 3 | C. Multilayer bus+metro accessibility: how much of a new line's benefit flows through bus transfers? | Ward-level accessibility gain split into metro-only vs bus-enabled parts; equity (Gini/Palma) | Medium | Medium (routing compute) | High (best showcase for Spark scaling) |

---

## 1. Corrections to the existing literature survey

- **"Wang et al. 2023, Beijing bus+subway"** is actually **Wang et al. (2021), "Big data-driven public transportation network: a simulation approach," *Complex & Intelligent Systems*, doi:10.1007/s40747-021-00462-2**. Please check the year in your slides. It is a combined bus+subway network, so your claim that "nobody combines bus and metro" is **not true globally**. Reframe the gap as *Bengaluru/India-specific, using observed ridership and a causal design*.
- "Bus and metro usually analysed separately" is **also not strictly true for Bengaluru**. Gadepalli et al. 2022 and Hasan et al. 2025 / Deepa et al. 2022 both include bus–metro interaction. Cite them and state your delta (Section 3).

---

## 2. Data inventory (verified)

| Dataset | What / granularity | Period | Source and licence | Notes |
|---|---|---|---|---|
| **BMRCL station-hourly entries** | Station × date × hour boardings, 83 stations | 1–18 Aug 2025; **1–30 Sep 2025** | RTI by Vivek Matthew; [GitHub Vonter/bmrcl-ridership-hourly](https://github.com/Vonter/bmrcl-ridership-hourly) (ODbL; some content © BMRCL); also on [OpenCity](https://data.opencity.in/dataset/bmrcl-station-wise-ridership-data) (stated CC non-commercial) | Your XLSX is very likely this file. **Get the September file too**: it gives a 30-day post period. |
| **BMRCL station-hourly exits** | Station × date × hour alightings | 1–18 Aug 2025 | same | |
| **BMRCL station-pair hourly (OD)** | Origin × destination × date × hour, ~1.2 M rows; "enhanced" version adds stations travelled, fare slab, fare, revenue | 1–18 Aug 2025 | same | **The most valuable file.** Counts are fare-gate based: transfers inside the paid area are not counted as entries. A Green→Yellow trip appears as one OD pair. |
| **BMTC GTFS (unofficial)** | routes, stops, trips, stop_times (interpolated), shapes, fares; ~5,000 routes | Snapshots 2024-02 … **2025-08-04**, **2025-09-02**, 2025-10, 11, 12 … 2026-11-09 (git history) | [Vonter/bmtc-gtfs](https://github.com/Vonter/bmtc-gtfs) (ODbL), scraped from the Namma BMTC app; also in [Mobility Database mdb-2595](https://mobilitydatabase.org/feeds/gtfs/mdb-2595) | README warns timetables are inaccurate. Use **trip counts per route/stop per day** (robust), not minute-level times. |
| BMRCL GTFS (unofficial) | Built from OSM plus BMRCL headway timetables | Posted Jun 2026 | [Vonter/bmrcl-gtfs](https://groups.google.com/g/datameet/c/h5uI8DMlgi4) | Headway-based; fine for network topology and frequency. |
| Your BMTC stops/routes by ward (KML/CSV) | Static stop and route lists by ward | (older) | OpenCity | Use for ward joins; check against GTFS. |
| Ward boundaries + population | 198 wards with Census 2011 merged (CSV/GeoJSON/SHP); 243-ward 2022 map; 2025 GBA 5-corporation 369-ward map | 2011 / 2022 / 2025 | [suvajit/opendata](https://github.com/suvajit/opendata/tree/master/BBMP/data), [OpenCity BBMP ward map 2022](https://data.opencity.in/dataset/bbmp-ward-information/resource/9423dbca-db2b-47df-823e-8546f4fb8f2a) | Population is 2011. Optionally downscale with a gridded population product. |
| OSM | Walk network, POIs, built-up area | current | openstreetmap.org | For walking-transfer distances. |
| BMTC aggregate operations | Fleet, km, revenue by year | 2012–2026 | [OpenCity BMTC performance](https://data.opencity.in/dataset/bmtc-operation-performance-data) | BMTC **route-level ridership is NOT open**: shared only under NDA. An Azim Premji Univ. study used 2.89 crore trip records (Jan 2023–Jan 2025) but the data is not public. You could file an RTI for route-wise daily ticket counts on Hosur Road routes for Aug 2025 as an upside extension. |

### Natural experiments and timeline (verified from news)
- **10 Aug 2025 (Sun):** Yellow Line inaugurated. **11 Aug 2025 (Mon):** commercial service, 3 trains, ~25-min headway, RV Road is the only interchange ([Deccan Herald](https://www.deccanherald.com/india/karnataka/bengaluru/commuters-give-a-thumbs-up-as-yellow-line-operations-begin-3675231); [Wikipedia](https://en.wikipedia.org/wiki/Yellow_Line_(Namma_Metro))).
- **11 Aug 2025:** BMTC launches feeder routes (MF-22 family; 12 buses, 4 routes, 96 trips/day) and moves bus stops closer to Yellow stations ([Deccan Herald](https://www.deccanherald.com/india/karnataka/bengaluru/bmtc-launches-12-feeder-buses-for-last-mile-links-on-yellow-line-3678164)).
- **10 Sep 2025:** 4th train, headway **25 → 19 min**; BMRCL reports only +5–6% Yellow ridership ([Deccan Herald](https://www.deccanherald.com/india/karnataka/bengaluru/namma-metro-bengaluru-yellow-line-trains-to-run-every-19-mins-from-september-10-3719425)). This **falls inside your September station-hourly data**.
- **1 Nov 2025:** 5th train, 15-min peak headway (outside data window).
- **13 Nov 2026 (flag-off) / 14 Nov 2026 (public):** **Pink Line** elevated section Kalena Agrahara–Tavarekere (6 stations, 7.5 km) opened, with ~33k riders on day 1 up to 7 pm ([NewsKarnataka](https://newskarnataka.com/bengaluru/bengaluru-pink-line-records-33409-riders-on-day-one/15112026/); [Oneindia](https://www.oneindia.com/bengaluru/namma-metro-pink-line-7-5-km-stretch-connecting-kalena-agrahara-and-tavarekere-to-open-on-november-8248555.html)). This is a **future out-of-sample test** (an RTI for Nov–Dec 2026 is possible; the Nov 2026 GTFS snapshot already exists).
- **Confounders inside the Aug window:** 15 Aug (Independence Day, Fri), 16 Aug (Janmashtami, ISKCON spike at Mahalakshmi), and the Lalbagh Flower Show (around Independence Day; Lalbagh station spike). Handle these with date FE plus dropping or flagging Lalbagh/Mahalakshmi for affected days.

---

## 3. Prior art map (closest papers; what they do and how you differ)

| # | Paper | What it does | Delta for Team 15 |
|---|---|---|---|
| 1 | **Hasan, Nirmale, Deepa, Pinjari (2025)**, *TR Part A* 200:104638 | Direct-demand log-linear models of station boardings/alightings by direction; 40 stations, 2 corridors; downstream/upstream accessibility; **metro–bus competition and complementarity**; spatial dependence; policy simulation says more feeder buses help | **Closest paper.** Cross-sectional and pre-Yellow, so it cannot identify causal effects. Yours: a **quasi-experiment** (line opening + headway change), **hourly OD**, 83 stations / 3 lines, bus exposure from **dated GTFS snapshots**, and the bus supply response. |
| 2 | **Deepa, Pinjari, Nirmale, Srinivasan, Rambha (2022)**, *TR Part A* 163:126–147 | Direct-demand model of **BMTC** stop-cluster ridership; inter-route competition/complementarity incl. with metro; frequency endogeneity (IV) | Bus side only, using non-public BMTC data. You flip it: open metro OD data plus GTFS. |
| 3 | **Gadepalli, Gumireddy, Bhamidipati, Cats (2022)**, *Case Studies on Transport Policy* 10:940–947 | Impact of first Namma Metro lines on BMTC: 86% of 2,203 routes overlap metro; buses preferred <5 km, metro >5 km; only 6% of routes have ≥10% of trips parallel to metro; rationalisation framework | Descriptive before/after, pre-COVID, non-public ticketing. Yours: causal, **2025 line**, open data, metro-side response, replicable. |
| 4 | Diagram Chasing blog / [blr-metro-ridership analysis](https://blr-metro-ridership.netlify.app/analysis) (2025) | Descriptive analysis of the same RTI data; per-station weekday linear model with day-of-week control, p<0.09; Lalbagh +38.7%, Chickpete/Banashankari −13–14% (*hypothesised* to be bus-related) | Not peer-reviewed, **no bus data**, no causal design. **Their bus hypothesis is exactly what Idea A tests.** Cite it. |
| 5 | **Lu, Zhang, Ong, Kwan, Xie (2026)**, *J. Planning Education and Research* 46(1):72–87 | Spatial interrupted time series: metro expansion creates network spillovers on existing lines, decaying with distance (Shenzhen) | Metro only; China; smart-card data. Yours adds the **bus channel** and an Indian setting. |
| 6 | **Ding, Tang, Wang, Zhao (2025)**, *J. Transport Geography* 125:104205 | Spatiotemporal lag FE models of station ridership growth under expansion (Shanghai 2014–19); nearby stations compete, same-line stations complement | Metro only; annual data. |
| 7 | **Liu, Jin, Zhang, Gao, et al. (2026)**, *TR Part A* 212:105182 | PSM-DiD across Chinese cities: 1% more metro density gives −2.3% bus, +1.4% total PT ridership | City-level aggregate. Yours is station/OD-level, within a city. |
| 8 | **Gao, Guo, Long, Cui, Li (2022)**, *Travel Behaviour and Society* 26:221–230 | Xiamen: same IC-card holders before/after metro opening; switching peaks at ~4 collinear stops | Needs bus smart cards (not available in Bengaluru). Your GTFS "collinearity" exposure is the open-data analogue. |
| 9 | **Brands, Dixit, van Oort (2020)**, *EJTIR* 20(4):335–353 | Amsterdam North–South line: +4% ridership, shift from tram/bus to metro | Before/after with smart cards; no exposure gradient. |
| 10 | Shanghai cellular-signalling catchment study ([TRID 2583060](https://trid.trb.org/View/2583060)) **[authors/venue unverified]** | Only ~2% of new-line riders diverted from existing lines; catchments shift with transfer status | Cellular data; metro only. |
| 11 | **Wang et al. (2021)**, *Complex & Intelligent Systems* | Beijing bus+subway complex-network simulation with smart-card data | Topology/optimisation, not ridership causality. |
| 12 | Shanmukhappa (2018), PhD thesis, PolyU ([handle](https://theses.lib.polyu.edu.hk/handle/200/9946)) | Bus+metro networks of Hong Kong, London, **Bengaluru**; layers combined via spatial amalgamation; robustness | Topological, old networks, no ridership. Relevant to Idea C. |
| 13 | Šfiligoj, Massobrio, Cats (2026), arXiv:2603.21130 | Review of multilayer public-transport networks and research agenda | Use as framing citation for Idea C. |
| 14 | **Srinivasa, Murthy, Chandrasekharan (2025)**, IIMB WP 723 | Spatial decomposition framework: 245 last-mile stops, feeder networks for 92 stations; ~93% population walkable coverage with feeders | Planning/design, no observed ridership. Use as benchmark for the Idea B feeder-gap list. |
| 15 | **Kori & Srikanth (2025)**, *Periodica Polytechnica Transp. Eng.* 53(4):462–471 | Sustainability Integration Index (18 indicators, expert weights) for metro–feeder integration in Bengaluru | Survey/expert-weight index. Yours is data-driven and validated on ridership. |
| 16 | CSTEP (2017/2018) reports for BMTC: [Route Integration](https://cstep.in/drupal/sites/default/files/2020-06/1_Route_Integration_KEA_Addressed.pdf), [Impact of Metro on Bus Ridership](https://cstep.in/drupal/sites/default/files/2020-04/Impact%20of%20Metro%20on%20Bus%20Ridership.pdf) | Surveys at 12 stations (~38% shifted from BMTC to metro, per search snippet **[figure unverified]**); feeder routes for 4 stations | Grey literature; survey-based. |
| 17 | **Ding, Liang, Wang, Tang, Zhou, Zhao (2024)**, Metro-MGAT, ACM UrbanAI '24 | Multi-graph attention for ridership at **new** stations in expanding networks (Shanghai) | Metro-only features. Idea B adds bus features and tests on Bengaluru's Yellow/Pink. |
| 18 | WRI India (2023), *Improving metro access in India* (doi:10.46830/wriwp.23.00009) | 7,200 metro users in Nagpur/Delhi/Bengaluru; walking + shared modes >75% of last mile | Context for access assumptions (400–800 m catchments). |
| 19 | Berrebi, Joshi, Watkins, "On Ridership and Frequency," arXiv:2002.02493 | Bus frequency elasticity: inelastic within-route over time, higher for low-frequency routes | Benchmark for the 25→19 min headway elasticity in Idea A. |
| 20 | Adhvaryu et al. 2019 (PTAL Surat), already in your survey | PTAL | Baseline accessibility metric for Idea C. |

**Gap statement for the paper:** *"No study has exploited a metro line opening in an Indian city as a quasi-experiment, nor tested whether the structure of the co-existing bus network moderates how existing metro stations and OD flows respond. Existing Bengaluru studies are cross-sectional (Hasan et al. 2025), descriptive (Gadepalli et al. 2022) or rely on non-public ticketing data."*

---

## 4. Idea A (RECOMMENDED): The Yellow Line as a natural experiment, and whether the bus network decides who wins and loses

### Pitch
On 11 Aug 2025 Bengaluru opened the Yellow Line, which connects through a single interchange (RV Road). You have hourly OD metro flows for 10 days before and 8 days after, hourly station entries for September (including a headway cut on 10 Sep), and BMTC GTFS snapshots from 4 Aug and 2 Sep 2025. Some existing metro stations (e.g., Banashankari, Chickpete) were plausibly **bus-to-metro transfer points for trips to Hosur Road / Electronic City**. Once the Yellow Line opened, those riders could reroute (bus → Yellow directly, or metro → RV Road → Yellow). Other stations gained because they now offer a one-seat-plus-transfer route. We build a **station-level "bus-mediated exposure" index from GTFS** and estimate, with an event-study / continuous-treatment DiD, how much of the reshuffling of metro ridership is explained by bus-network overlap with the new corridor. **Neither bus-only nor metro-only data can answer this question.**

### Research questions and hypotheses
- **RQ1 (network spillover):** How did entries/exits and OD flows at the 67 pre-existing stations change after the Yellow Line opened, net of common shocks?
- **RQ2 (bus mediation, the core):** Is the change explained by bus-network exposure?
  - **H2a (substitution):** Stations whose 400 m bus catchment carries a high share of BMTC trips that also serve the Yellow corridor (stops within 800 m of Yellow stations) **lose** entries, especially in peaks.
  - **H2b (complementarity):** Stations with high metro-path accessibility to RV Road and low bus overlap **gain** OD flows to Yellow destinations.
- **RQ3 (OD restructuring):** Which origins generate the new cross-line OD pairs (Purple/Green → Yellow)? Does each origin's share correlate with the *absence* of a direct bus alternative between that origin and the Yellow corridor (computed from GTFS)?
- **RQ4 (dose-response):** Did the 10 Sep 2025 headway cut (25→19 min, +32% frequency) raise Yellow-station entries? What is the implied frequency elasticity, and does it differ for stations with new BMTC feeders (GTFS Aug→Sep diff)?
- **RQ5 (bus supply response):** How did BMTC supply around Yellow stations change between the 2025-08-04 and 2025-09-02 snapshots (new routes, trips/day, stops moved)? Was the change targeted at stations with low early ridership?

### Method (step by step)
1. **Ingest** (Spark): RTI parquet/CSVs; 20+ GTFS snapshots (2024-02 … 2026-11) into HDFS as partitioned parquet (`snapshot_date`).
2. **Crosswalk:** metro station coordinates (OSM / BMRCL GTFS) linked to BMTC stops within 400/800 m walking (OSM network, or Euclidean with sensitivity). Use a Spark/Sedona distance join.
3. **Exposure variables per existing station s** (from the 2025-08-04 snapshot):
   - `BusFeed_s`: daily bus trips at stops within 400 m.
   - `YellowOverlap_s`: share of those trips on routes that also stop within 800 m of any Yellow station (a direct bus link between s's catchment and the Yellow corridor).
   - `Collinear_s`: route-overlap length with the Yellow alignment (Gao et al. 2022's "collinear stops" analogue).
   - `MetroPathToRV_s`: network distance (stations) to RV Road.
4. **Panel:** station × date × hour (entries and exits), 1–18 Aug + 1–30 Sep 2025. OD × date × time-band for Aug.
5. **Models:**
   - Event study: `log(1+y_{s,d,h}) = α_s×h + γ_{d,h} + Σ_k β_k · 1[d ∈ k] · Exposure_s + ε`. Station×hour FE absorb station profiles; date×hour FE absorb holidays and weather common to all stations. Also estimate with **PPML** (Poisson pseudo-ML) because counts have zeros.
   - Continuous-treatment DiD with interactions (peak/off-peak, weekday/weekend). Cluster SEs by station; use wild-cluster bootstrap (67 clusters).
   - OD-level gravity DiD: `flow_{o,d,t}` with o×d FE, o×t and d×t FE; treatment = new path via RV Road × bus-alternative indicator from GTFS.
   - **Placebos:** fake opening dates (5 Aug, 7 Aug); stations at the far ends of Purple/Green with near-zero exposure; Sept-only pre/post around 10 Sep for RQ4 (Yellow vs. non-Yellow stations, synthetic control as robustness).
   - Robustness: drop 15–16 Aug; drop Lalbagh/Mahalakshmi; 400 vs 800 m buffers; exposure from Sep snapshot.
6. **RQ5:** GTFS diff (Aug→Sep 2025, and the monthly series to 2026). Report routes added/removed/rerouted near Yellow stations. Event plot of bus trips/day within 400 m of Yellow vs. control stations across snapshots (2024-02 → 2026-11), giving a supply-side event study.
7. **Scalability (secondary):** time the exposure join and panel build on 1/2/4/8 executors and on 1×/5×/20× data (stacking GTFS snapshots, replicating the OD panel). Report strong/weak scaling.

### Expected figures and tables
- Fig 1: Map of 83 stations coloured by `YellowOverlap_s` with the Yellow alignment and BMTC routes.
- Fig 2: Event-study coefficients by day (pre-trend test) for high- vs low-exposure stations.
- Fig 3: OD chord/flow map of new cross-line flows by origin, with bus-alternative overlay.
- Fig 4: Sept headway-cut event study for Yellow stations, with the implied elasticity.
- Fig 5: Bus supply around Yellow stations across GTFS snapshots (2024–2026).
- Table: main DiD estimates with robustness columns; table of Spark scaling.

### Evaluation and baselines
- Baseline 1: naive per-station before/after (replicating the blog's approach) vs. FE-DiD, to show how inference changes.
- Baseline 2: metro-only exposure (distance to RV Road) vs. metro+bus exposure. **The incremental R² / likelihood-ratio test of the bus terms is the key "joint data" result.**
- Pre-trend tests; placebo dates; randomisation inference (permute exposure across stations).

### Closest work and delta
Hasan 2025 (cross-sectional, no shock), Gadepalli 2022 (descriptive, old line), Lu 2026 / Ding 2025 (metro-only spillovers, China), Gao 2022 (smart-card collinearity, China), blog (no bus, no design). **Delta: the first quasi-experimental estimate of a new metro line's effect on existing-station and OD ridership in India, with bus-network structure from dated open GTFS as the moderating mechanism, plus the matching bus supply response.**

### Target venues
- **Tier A (stretch):** *Journal of Transport Geography*; *Transportation Research Record* (TRB Annual Meeting route, typical deadline ~1 Aug; check current call).
- **Tier B (realistic primary):** ***Case Studies on Transport Policy*** (published Gadepalli 2022; Scopus Q1/Q2); ***Transportation in Developing Economies*** (Springer); *Findings* (short, fast, suited to one clean natural-experiment result; findingspress.org).
- **Tier C (conference, Scopus-indexed):** IEEE ITSC; IEEE BigData workshops; ACM SIGSPATIAL UrbanAI workshop; CTRG / TPMDC in India (Springer Lecture Notes in Civil Eng.). *Check each venue's current CFP; deadlines not verified here.*

### Risks and mitigations
| Risk | Mitigation |
|---|---|
| Short pre-window (10 days) and holiday overlap | Date×hour FE; drop 15–16 Aug; Sept data extends the post period to 30 days; report both short- and medium-run effects. |
| No pure control group (network SUTVA violation) | Continuous exposure design; low-exposure end-of-line stations; randomisation inference; frame the estimand as *differential* response. |
| GTFS timetables inaccurate | Use trip **counts** and route-stop membership, not times; sensitivity with route counts only. |
| Your XLSX may be station-only, not OD | Download stationpair + September files from GitHub (ODbL). Cite the RTI source and the licence. |
| Gate counts exclude paid-area transfers | OD captures true origin/destination; interpret station entries accordingly. |
| No BMTC ridership | State as a limitation. Optional RTI to BMTC for route-wise daily tickets on ~20 Hosur Road routes for Aug–Sep 2025 (strong upside if granted). |

---

## 5. Idea B: A bus–metro feeder/competition index for Bengaluru, tested on stations the model has never seen

### Pitch
Build an open, reproducible station-level index that separates **feeder bus supply** (routes roughly perpendicular to the metro, ending or turning near stations) from **competing bus supply** (routes collinear with metro segments), using GTFS geometry and trip counts. Then show the index explains hourly metro boardings/alightings and OD trip-length structure better than metro-only features. **Key test: train on Purple+Green, predict the Yellow Line stations (opened Aug 2025), then predict the six Pink Line stations (opened 14 Nov 2026) before their ridership is known**, i.e. a pre-registered forecast. Residuals give a ranked **feeder-gap list** (stations under-performing given land use), compared with IIMB WP 723's proposed feeder network and the BMTC MF routes actually added.

### RQs
1. Do GTFS-derived feeder and competition indices add explanatory power for station ridership beyond population, land use and network centrality?
2. Does the model transfer to new stations (Yellow, then Pink)?
3. Which stations have the largest feeder gap, and did BMTC's 2025–26 feeder additions (GTFS diffs) target them?

### Method
1. Per station and time-band: route-angle classification (bearing of route shape within 1 km relative to the metro line bearing); trips/hour by class; walking-distance decay.
2. Controls: ward population (2011, area-weighted to 800 m catchment), OSM POI/built-up, betweenness from the metro graph, distance to CBD, interchange dummy.
3. Models: PPML / negative binomial with spatial lag (SAR); gradient boosting; a light GNN (GraphSAGE/GAT on metro graph with bus features), compared with Metro-MGAT-style metro-only features.
4. Validation: leave-line-out (train P+G → test Yellow); temporal (Aug vs Sep); **Pink forecast** published as a preprint before the RTI data arrives (file an RTI for Nov–Dec 2026 hourly data now).
5. Feeder-gap ranking from residuals, overlaid on IIMB WP 723 recommendations and the Aug 2025 → Nov 2026 GTFS feeder additions.

### Outputs
Index maps; ablation table (metro-only vs +bus); MAPE on held-out lines; ranked gap list.

### Delta
Hasan 2025 includes competition/complementarity but on 40 stations with one cross-section and no new-station transfer test. Metro-MGAT has no bus features and no Indian data. Kori & Srikanth 2025 is expert-weighted and not validated on ridership. **Delta: an open-data, GTFS-geometric decomposition of bus supply validated out-of-sample on two newly opened lines.**

### Venues
*Transportation in Developing Economies*; *Case Studies on Transport Policy*; IEEE ITSC / UrbanAI workshop (GNN angle). The dataset/crosswalk could go to *Data in Brief* (see Section 7).

### Risks
Small n (83 stations → 89 with Pink): use hourly profiles to enrich the target, use regularisation, report CIs. Pink data may not arrive within the semester: keep it as "forecast published; evaluation pending." Route-angle heuristics: validate on 20 manually labelled routes.

---

## 6. Idea C: Multilayer bus+metro accessibility, and how much of a new line's benefit flows through bus transfers

### Pitch
Build a time-expanded multilayer network (BMTC GTFS layer + BMRCL GTFS layer + walking interlayer links ≤400 m). Compute ward-level cumulative accessibility (population or jobs reachable within 45/60 min) **before and after the Yellow Line** (Aug vs Sep 2025 GTFS) and after the Pink Line (Nov 2026). Decompose each ward's gain into (i) metro-only access, (ii) gains that **require a bus leg**. Counterfactual: delete interlayer edges, or delete the new feeder routes. Validate: do wards with larger bus-enabled gains show larger observed increases in metro OD flows from their nearest stations?

### RQs
1. What share of the Yellow Line's accessibility benefit depends on bus–metro transfers?
2. How is the gain distributed across wards (Gini, Palma; Shakti-relevant peri-urban east)?
3. Does modelled accessibility gain predict observed OD ridership change (link to Idea A)?

### Method
RAPTOR/r5-style routing on GTFS (r5py or OpenTripPlanner) for ward centroid pairs (198–369 wards × time slots × snapshots), parallelised over origins in Spark (a natural embarrassingly-parallel scaling experiment). 2SFCA/PTAL as baselines (Adhvaryu 2019).

### Delta
Shanmukhappa 2018 (topological, old Bengaluru network, no ridership), Wang 2021 (Beijing, simulation), Šfiligoj et al. 2026 (review). **Delta: a dated before/after multilayer accessibility decomposition for an Indian city, validated against observed metro OD change.**

### Venues
*Journal of Transport Geography*; *Transportation in Developing Economies*; *Environment and Planning B* (stretch); IEEE BigData workshop (Spark angle).

### Risks
Interpolated BMTC timetables, so use frequency-based routing and sensitivity bands. Jobs data is weak for Bengaluru, so use population/POIs. Compute cost: limit time slots, use ward centroids, and use Spark for scale.

---

## 7. Secondary contribution (any idea): an integrated open dataset

A cleaned, documented **BMTC-stop ↔ BMRCL-station crosswalk** with exposure features for every GTFS snapshot (2024–2026), joined to RTI hourly ridership, plus the Spark pipeline. Possible venue: *Data in Brief*. Respect ODbL share-alike, and note that OpenCity labels the ridership data CC-NC, so attribute both.

## 8. Ideas considered and killed

- **GNN ridership forecasting alone:** possible with metro-only data, 18 days is too short, and there are many Chinese GNN papers, so no novelty. Folded into B as an ablation.
- **Inferring bus→metro transfer volumes from aggregate counts:** no ground truth (no BMTC smart cards); unvalidatable (cf. hEART 2025 counts-based rail model).
- **Shakti scheme × metro:** BMTC trip data not public.
- **Feb 2025 fare hike impact:** outside the data window.
- **Dashboard / integrated platform:** not a research result; keep as a demo only.
- **Pure Hadoop vs Spark benchmarking:** not publishable in transport venues; keep as the secondary scaling section.

## 9. Recommendation and semester plan (Idea A, with B's index as a feature set)

- **Weeks 1–2:** download RTI parquet (Aug OD + Sep station) and GTFS snapshots 2025-08-04 / 2025-09-02 via git checkout; HDFS ingest; station crosswalk.
- **Weeks 3–4:** exposure variables; descriptive maps; replicate the blog's naive estimates.
- **Weeks 5–7:** FE/PPML event study, OD gravity DiD, placebos, Sept headway analysis.
- **Week 8:** GTFS supply-response series (2024–2026).
- **Weeks 9–10:** Spark scaling experiments; robustness.
- **Weeks 11–13:** write-up (aim at *Case Studies on Transport Policy* or *Transportation in Developing Economies*; TRB/TRR if timing fits). File the Pink Line RTI in week 1 for a follow-up paper (Idea B forecast test).

---

## 10. References (verified links)

**Data and context**
- Vonter, *bmrcl-ridership-hourly* (RTI, ODbL). https://github.com/Vonter/bmrcl-ridership-hourly (DATA.md lists periods and fields)
- Datameet post "Hourly station-pair ridership for Namma Metro in Bengaluru" (1 Oct 2025). https://groups.google.com/g/datameet/c/OEDChJDYS-E
- Diagram Chasing, "How Bangalore uses the metro" (2025). https://diagramchasing.fun/2025/how-bangalore-uses-the-metro ; analysis notebook https://blr-metro-ridership.netlify.app/analysis
- OpenCity, BMRCL Station-wise Ridership Data. https://data.opencity.in/dataset/bmrcl-station-wise-ridership-data
- Vonter, *bmtc-gtfs* (unofficial GTFS, ODbL; monthly snapshots incl. 2025-08-04, 2025-09-02). https://github.com/Vonter/bmtc-gtfs ; Mobility Database https://mobilitydatabase.org/feeds/gtfs/mdb-2595
- Vonter, *bmrcl-gtfs* (unofficial). https://groups.google.com/g/datameet/c/h5uI8DMlgi4
- BBMP ward data with Census 2011. https://github.com/suvajit/opendata/tree/master/BBMP/data ; OpenCity ward map 2022 https://data.opencity.in/dataset/bbmp-ward-information/resource/9423dbca-db2b-47df-823e-8546f4fb8f2a
- OpenCity BMTC operational performance data. https://data.opencity.in/dataset/bmtc-operation-performance-data
- Yellow Line opening: https://en.wikipedia.org/wiki/Yellow_Line_(Namma_Metro) ; https://www.deccanherald.com/india/karnataka/bengaluru/commuters-give-a-thumbs-up-as-yellow-line-operations-begin-3675231
- BMTC Yellow Line feeders: https://www.deccanherald.com/india/karnataka/bengaluru/bmtc-launches-12-feeder-buses-for-last-mile-links-on-yellow-line-3678164
- Yellow headway 19 min from 10 Sep 2025: https://www.deccanherald.com/india/karnataka/bengaluru/namma-metro-bengaluru-yellow-line-trains-to-run-every-19-mins-from-september-10-3719425
- Pink Line opening Nov 2026: https://www.oneindia.com/bengaluru/namma-metro-pink-line-7-5-km-stretch-connecting-kalena-agrahara-and-tavarekere-to-open-on-november-8248555.html ; https://newskarnataka.com/bengaluru/bengaluru-pink-line-records-33409-riders-on-day-one/15112026/
- Azim Premji Univ. Shakti/BMTC study (news coverage): https://www.theweek.in/wire-updates/national/2025/11/06/mds9-ka-shakti-scheme-study.html

**Academic**
- Hasan, N., Nirmale, S.K., Deepa, L., Pinjari, A.R. (2025). Modelling metro rail ridership at the station- and route-level: an application to analysis of metro ridership in Bengaluru, India. *TR Part A* 200, 104638. doi:10.1016/j.tra.2025.104638. https://econpapers.repec.org/RePEc:eee:transa:v:200:y:2025:i:c:s0965856425002666
- Deepa, L., Pinjari, A.R., Nirmale, S.K., Srinivasan, K.K., Rambha, T. (2022). A direct demand model for bus transit ridership in Bengaluru, India. *TR Part A* 163, 126–147. doi:10.1016/j.tra.2022.07.004. https://ideas.repec.org/a/eee/transa/v163y2022icp126-147.html
- Gadepalli, R., Gumireddy, S., Bhamidipati, S., Cats, O. (2022). Impact of introducing a metro line on urban bus services. *Case Studies on Transport Policy* 10, 940–947. https://pure.tudelft.nl/ws/portalfiles/portal/122274243/1_s2.0_S2213624X22000591_main.pdf
- Lu, D., Zhang, W., Ong, P.M., Kwan, M.-P., Xie, S. (2026). The Network Spillover Effects of Metro Expansion on Metro Usage: A Quasi-experimental Analysis in Shenzhen, China. *J. Planning Education and Research* 46(1), 72–87. doi:10.1177/0739456X251345403. https://research.tue.nl/en/publications/the-network-spillover-effects-of-metro-expansion-on-metro-usage-a/
- Ding, F., Tang, Y., Wang, Y., Zhao, Z. (2025). Unraveling the network effects in station ridership growth patterns under metro network expansion. *J. Transport Geography* 125, 104205. doi:10.1016/j.jtrangeo.2025.104205. https://ideas.repec.org/a/eee/jotrge/v125y2025ics0966692325000961.html
- Liu, M., Jin, S., Zhang, C., Gao, K., et al. (2026). Metro prosperity and bus decline: A causal relationship? A quasi-experimental study of 17 key cities in China. *TR Part A* 212, 105182. doi:10.1016/j.tra.2026.105182. https://research.chalmers.se/en/publication/553556
- Gao, Y., Guo, Z., Long, Y., Cui, Z., Li, X. (2022). Passengers' travel behavior before and after the adjustment of regular bus collinear sections: a case study in the incipient phase of metro operation in Xiamen. *Travel Behaviour and Society* 26, 221–230. https://wagner.nyu.edu/impact/research/publications/passengers-travel-behavior-and-after-adjustment-regular-bus-collinear
- Brands, T., Dixit, M., van Oort, N. (2020). Impact of a New Metro Line in Amsterdam on Ridership, Travel Times, Reliability and Societal Costs and Benefits. *EJTIR* 20(4), 335–353. doi:10.18757/ejtir.2020.20.4.4084. https://journals.open.tudelft.nl/ejtir/article/view/4084
- Wang et al. (2021). Big data-driven public transportation network: a simulation approach. *Complex & Intelligent Systems*. doi:10.1007/s40747-021-00462-2. https://link.springer.com/article/10.1007/s40747-021-00462-2
- Ding, F., Liang, Y., Wang, Y., Tang, Y., Zhou, Y., Zhao, Z. (2024). A Graph Deep Learning Model for Station Ridership Prediction in Expanding Metro Networks. ACM UrbanAI '24. doi:10.1145/3681780.3697247. https://dspace.mit.edu/handle/1721.1/157842
- Srinivasa, M., Murthy, R.V., Chandrasekharan, R. (2025). A spatial decomposition-based framework for building last-mile connectivity to urban public transit systems: Defining feeder networks for the metro rail in Bengaluru. IIMB WP No. 723. https://www.iimb.ac.in/sites/default/files/2025-08/WP%20No.%20723.pdf
- Kori, V., Srikanth, S. (2025). Evaluating the Sustainability of Metro and Feeder Bus Integration: A Bengaluru Metro Case Study in India. *Periodica Polytechnica Transp. Eng.* 53(4), 462–471. doi:10.3311/PPtr.38158. https://pp.bme.hu/tr/article/view/38158
- Šfiligoj, T., Massobrio, R., Cats, O. (2026). Multilayer public transport networks. arXiv:2603.21130. https://arxiv.org/abs/2603.21130
- Shanmukhappa, T. (2018). PhD thesis, Hong Kong Polytechnic University (bus+metro networks incl. Bengaluru). https://theses.lib.polyu.edu.hk/handle/200/9946
- Berrebi, S.J., Joshi, S., Watkins, K.E. On Ridership and Frequency. arXiv:2002.02493. https://arxiv.org/abs/2002.02493
- WRI India (2023). Improving metro access in India (working paper). doi:10.46830/wriwp.23.00009. https://wri-india.org/sites/default/files/Improving%20metro%20access%20in%20India_%20Working%20Paper.pdf
- CSTEP (2017). Route Integration (for BMTC). https://cstep.in/drupal/sites/default/files/2020-06/1_Route_Integration_KEA_Addressed.pdf ; CSTEP, Impact of Metro on Bus Ridership. https://cstep.in/drupal/sites/default/files/2020-04/Impact%20of%20Metro%20on%20Bus%20Ridership.pdf
- Shanghai new-line catchment study (cellular signalling). https://trid.trb.org/View/2583060 **[authors/venue unverified]**
- JpGU 2026 abstract "Evolving Metro Network Dynamics in Bengaluru: A Time-Series Typology of Ridership Patterns" **[title seen in search only; content unverified; check for overlap]**
