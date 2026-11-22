# Team 15 — Project context (from Team15_lit_survey.pptx)

**Title:** Big Data Analytics for Bengaluru Public Transport Optimization (undergrad CSE team, advisor Asst. Prof.)
**Stack planned:** Hadoop HDFS, Apache Spark / PySpark, Spark SQL; measure Spark response time vs data size.
**Data in hand:**
- BMTC bus stops (accessible stops data), BMTC stops & routes by ward (KML/CSV)
- BMRCL (Namma Metro) station-wise *hourly* ridership, August 2025 (XLSX)
**Core idea the team wants to pursue:** most papers analyse EITHER bus OR metro; combine BMTC + BMRCL data.

**Papers already in the survey:**
1. Adhvaryu et al. 2019 — PTAL mapping, Surat
2. Miftah et al. 2025 — Big data for smart-city traffic management (Hadoop/Spark)
3. Wang et al. 2023 — Big-data-driven bus+subway network, Beijing, complex network simulation (NOTE: already combines bus+metro!)
4. Melo et al. 2024 — Demand-responsive transport, Porto, mobile data
5. Ushakov et al. 2022 — Big data in smart-city transport infrastructure
6. Nesmachnow et al. 2023 — Bus travel time characterization, Montevideo, big data
7. Rakesh et al. 2018 — Big data at BMTC case study (Bengaluru)
8. Oladimeji et al. 2023 — Smart transportation overview
9. Yadav 2025 — Survey on public transport optimization with real-time analytics

**Gaps they identified:** no integrated processing framework; fragmented formats (CSV/KML/XLSX);
little Bengaluru-specific network analysis; bus and metro usually analysed separately.
