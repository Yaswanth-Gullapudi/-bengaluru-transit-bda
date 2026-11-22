# Team 15: Independent novelty and publishability audit of `01_research_proposals.md`

*Reviewer: novelty-reviewer agent. Date: 2026-11-21. I did not write the proposals and have no stake in them. My starting assumption was that each idea had already been done; an idea scored higher only when my own searching failed to find prior work. About 30 web searches and fetches, plus a GitHub API check of the GTFS commit history and a full-text read of Gadepalli et al. 2022. Several publisher pages (ScienceDirect, T&F, Deccan Herald) returned 403. Where I could not open a source, I say so.*

---

## 0. Summary table

| Idea | Novelty (1–5) | Closest work | Conference odds (Scopus IEEE/Springer) | Mid-tier journal odds (CSTP / TiDE / Findings / JTG) | Top venue | Verdict |
|---|---|---|---|---|---|---|
| **A. Yellow Line natural experiment × bus-overlap exposure** (as written) | **3** | Lu et al. 2026 JPER (new-line spillovers, Shenzhen); Chai, Sun & Yin 2025 TR-A 199 (metro–bus overlap as moderator, staggered DiD); Hasan et al. 2025 TR-A (Bengaluru metro–bus competition); Diagram Chasing blog (same data, same bus hypothesis) | ~55% | ~25% | ≤3% | **Pursue with changes** |
| A′. A, re-scoped (OD diversion test + longer pre-period via RTI + Pink Line replication) | 3.5 | as above | ~70% | ~45% (Findings / CSTP / TiDE) | 10–15% (JTG/TRR) | **Best path** |
| **B. Feeder/competition index + new-line transfer test** | **2** | Hasan et al. 2025 (feeder and parallel bus routes in Bengaluru station model); Ding et al. 2024 Metro-MGAT (new-station prediction); Lim 2025 MIT thesis (GTFS competing/complementary route DDM); Kori & Srikanth 2025 | ~45% | ~15% | <3% | **Drop as a standalone paper.** Fold the index into A as covariates. |
| **C. Multilayer bus+metro accessibility before/after** | **2** | Before/after GTFS accessibility for new lines (Oslo Fornebu, *Findings*; Brussels arXiv 2509.22223; Bogotá R5R, Zenodo 19420783; Guangzhou loop line 2026); Bengaluru ward equity (CSTP 2022, S2213624X22001948); Bengaluru feeder equity 2026 (T&F, 10.1080/29941849.2026.2713264) | ~55% (Spark/systems angle at IEEE BigData workshops) | ~20% | <3% | **Pursue with changes, as the secondary systems paper only** |
| Sec. 7. Integrated crosswalk dataset (*Data in Brief*) | 2–3 | Vonter repos themselves | n/a | ~35% (licence risk) | n/a | **Pursue with changes**: settle the licence first |

---

## 1. Fact-check of key claims

| Claim in proposals | Status | Evidence |
|---|---|---|
| RTI data: station-hourly and station-pair-hourly cover 1–18 Aug 2025; station-hourly also covers 1–30 Sep 2025 | **Verified** | [DATA.md](https://github.com/Vonter/bmrcl-ridership-hourly/blob/main/DATA.md): station hourly "1st August 2025 to 18th August 2025" and "1st September 2025 to 30th September 2025"; station pair "1st August 2025 to 18th August 2025". **No September station-pair file.** DATA.md does **not** clearly state whether *exits* exist for September. Check before planning exit-based September analyses. |
| Yellow Line inaugurated 10 Aug 2025 (Sun), commercial service 11 Aug; 19.15 km, 16 stations; 3 trains, ~25 min headway | **Verified** | [Wikipedia](https://en.wikipedia.org/wiki/Yellow_Line_(Namma_Metro)); [DH 1M riders on 11 Aug](https://www.deccanherald.com/india/karnataka/bengaluru/bengaluru-metro-ridership-crosses-1-million-for-the-first-time-after-yellow-line-opens-3677771) |
| 10 Sep 2025: 4th train, headway 25 → 19 min; BMRCL reported +5–6% | **Verified, but the proposal omits a confound** | [DH](https://www.deccanherald.com/india/karnataka/bengaluru/namma-metro-bengaluru-yellow-line-trains-to-run-every-19-mins-from-september-10-3719425), [DH "higher frequency boosts ridership"](https://www.deccanherald.com/india/karnataka/bengaluru/yellow-line-higher-frequency-boosts-ridership-3722198), [Swarajya](https://swarajyamag.com/amp/story/infrastructure/bmrcl-introduces-fourth-train-on-yellow-line-cutting-waits-to-19-minutes-amid-rising-metro-ridership-in-bengaluru). **On the same day, first service moved from 6:30 am to 6:00 am (Mon–Sat).** The +5–6% is a day-1 figure only. |
| 1 Nov 2025: 5th train, 15-min peak | Verified | [Oneindia](https://www.oneindia.com/bengaluru/starting-today-namma-metro-adds-fifth-train-to-yellow-line-with-15-minute-peak-hour-service-7904505.html) |
| BMTC GTFS rebuilt 2025-08-04 and 2025-09-02 | **Verified** | GitHub API commit log of Vonter/bmtc-gtfs: "Refetch data and recreate GTFS for August 2025" (2025-08-04T14:01Z) and "…for September 2025" (2025-09-02T04:31Z). README caveat: **only routes with working live tracking are included**, so snapshot-to-snapshot differences can come from tracking coverage, not service changes. |
| Pink Line (Kalena Agrahara–Tavarekere/S.G. Palya, 6 stations, 7.5 km) flagged off 13 Nov 2026, public 14 Nov 2026 | **Verified** | [Oneindia flag-off](https://www.oneindia.com/bengaluru/bengaluru-pink-line-metro-pm-modi-to-flag-off-7-5-km-kalena-agrahara-tavarekere-stretch-at-12-45-pm-8258445.html), [newkerala 14 Nov](https://www.newkerala.com/news/a/pink-line-metro-thrown-open-public-bengaluru-minister-951.htm). The "33,409 riders day 1" figure is **unverified** (I did not open that source). |
| Lalbagh flower show "around Independence Day" | **Understated** | It ran about **7/8 Aug to 17/18 Aug 2025** ([Oneindia](https://www.oneindia.com/bengaluru/lalbagh-independence-day-flower-show-2025-know-date-timings-ticket-price-and-more-7799727.html)), so it **straddles the treatment date**. Lalbagh's "+38.7%" (the blog's top winner) is very likely mostly the flower show. |
| CSTEP: ~38% shifted from BMTC to metro | Verified via search snippet of the CSTEP report | [CSTEP](https://cstep.in/drupal/sites/default/files/2020-04/Impact%20of%20Metro%20on%20Bus%20Ridership.pdf) |

## 2. Citation spot-check

| Reference | Exists? | Described correctly? |
|---|---|---|
| Hasan, Nirmale, Deepa, Pinjari 2025, TR-A 200:104638 | Yes ([EconPapers](https://econpapers.repec.org/RePEc:eee:transa:v:200:y:2025:i:c:s0965856425002666)) | Mostly. 40 stations, 2 corridors, metro–bus competition and complementarity, spatial dependence, station random effects. The abstract does **not** state "cross-sectional"; the random effects suggest repeated observations (direction/period). "Cannot identify causal effects" is a fair characterisation, but say "no exogenous shock" rather than "cross-sectional" unless you confirm it from the full text. |
| Deepa et al. 2022, TR-A 163:126–147 | Yes | Plausible (not opened in full). |
| Gadepalli, Gumireddy, Bhamidipati, Cats 2022, CSTP 10:940–947 | Yes (I read the full text) | **Partly misdescribed.** It compares BMTC KPIs at **Jan 2017 / Jan 2020 / Mar 2021** using ETM bus ticketing and metro OD data. 2,203 routes is confirmed. Buses are mostly <5 km and metro mostly 5–15 km (61–64%), which is consistent. I could **not find the "86% of routes overlap" or "6% of routes with ≥10% parallel trips" figures** in the extracted text (parallel routes are defined there as >25% of stops within 400 m). Re-check those numbers before citing them. |
| Diagram Chasing blog / netlify analysis | Yes | Correct: per-station `daily_ridership ~ after_yellow_line + wday`, weekdays only, 15–16 Aug dropped, p<0.09, no multiple-testing correction. **Important:** the blog article itself already attributes the Chickpete/Banashankari drops to their role as **bus boarding points for Electronic City**. The core hypothesis of Idea A is therefore public and has already been stated; it has not been tested. |
| Lu, Zhang, Ong, Kwan, Xie 2026, JPER 46(1):72–87 | Yes | Correct. |
| Ding et al. 2025 JTG 125:104205; Ding et al. 2024 Metro-MGAT | Yes (index pages) | Correct. |
| Liu, Jin, Zhang, Gao et al. 2026, TR-A 212:105182 | Yes | Figures (−2.3% bus, +1.4% PT per 1% metro density) confirmed. The abstract says **281 cities, 2010–2022**, although the title says "17 key cities". Clarify which. |
| Gao et al. 2022 TBS; Brands et al. 2020 EJTIR; Wang et al. 2021 CIS | Yes | Fine. |
| Shanghai TRID 2583060; JpGU 2026 abstract | Partly | The JpGU 2026 "Evolving Metro Network Dynamics in Bengaluru" talk exists (session HGG03-08). Its keywords are **station entry flows, DTW clustering**. The abstract text was not retrievable, so it **may use the same RTI data**. Email the authors or watch for a paper. |

No fabricated citations found. One misdescription (Gadepalli figures) and one over-claim (Hasan "cross-sectional").

### Important prior work the proposals missed
- **Chai, Sun & Yin (2025), TR-A 199**, "Navigating the impact of metro network on bus ridership: insights into the interdependency between metro and bus systems" ([IDEAS](https://ideas.repec.org/a/eee/transa/v199y2025ics096585642500223x.html)). A staggered DiD over 284 Chinese cities (2008–2021) that explicitly models **metro–bus spatial overlap, service equilibrium and service match as moderators**, with distance-decay bands. "Bus overlap moderates the metro effect" is therefore **already a published idea** at city level. Your delta has to be station/OD level and India.
- **Park & Eom (2024)**, intervention analysis of a new railway line's effect on ridership in Seoul, with a focus on transfer stations ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1226798824037577)). Fu et al. (2018), *J. Adv. Transp.*, Nanjing Line 4 smart-card study: existing stations on other lines lose flow after a new line opens ([Wiley](https://onlinelibrary.wiley.com/doi/10.1155/2018/9247102)). Together these make "new line redistributes ridership on existing stations" a known phenomenon.
- **CiSTUP–BMTC research booklet (IISc, Oct 2023)**: key finding that BMTC routes with high metro overlap lose riders ([PDF](https://cistup.iisc.ac.in/CiSTUP_Website/files/CiSTUP_BMTC%20Research%20Booklet_10Oct2023.pdf); fetch failed, finding seen via search snippet and [inkl coverage](https://inkl.com/news/reliability-key-to-making-public-transport-a-success)).
- **IISc (2026) Yellow Line final project report**: survey of ~600 commuters/households plus a 6-month follow-up on travel behaviour and well-being ([PDF](https://civil.iisc.ac.in/~ashishv/beta/banner/6143661cfe154857ef7956c86b159b6a26.pdf)). This is the only academic Yellow-Line-specific study I found. It is survey-based, not ridership-based, but cite it.
- **Lim (2025), MIT thesis**: GTFS-derived competing/complementary route variables in direct-demand models ([DSpace](https://dspace.mit.edu/bitstream/handle/1721.1/162329/lim-tmsl-smcts-dusp-2025-thesis.pdf)). Directly undercuts Idea B's methodological novelty.
- **Bengaluru feeder-equity paper (2026)**, T&F, doi:10.1080/29941849.2026.2713264 (ward-level feeder accessibility, need index; 403, abstract via search). **Bengaluru PT equity (CSTP 2022)**, S2213624X22001948 (198 wards, including future metro phases). Both are close to Idea C.
- GTFS before/after accessibility for new lines: Oslo Fornebu line ([*Findings*](https://findingspress.org/api/v1/articles/126523-accessibility-effects-of-a-new-metro-line.pdf)); Brussels Metro 3 ([arXiv 2509.22223](https://arxiv.org/pdf/2509.22223)); Bogotá synthetic GTFS + R5R ([Zenodo](https://zenodo.org/records/19420783)); Guangzhou loop line (2026, [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0143622826001402)).
- Other users of the same RTI data: the OpenCity revenue analysis by the data requester, [ridership.bengawalk.com](https://ridership.bengawalk.com), and Diagram Chasing. **No Kaggle notebook and no peer-reviewed paper on this RTI data found.** No GitHub analysis of metro–bus overlap built on Vonter/bmtc-gtfs found; its `analysis.py` only exports a network GeoJSON.

---

## 3. Idea A: Yellow Line natural experiment with bus-overlap exposure

### Novelty: 3/5
I searched about 12 query variants: metro opening DiD, existing-station spillover, bus overlap moderator, India/Delhi/Chennai/Mumbai/Hyderabad quasi-experiment, Yellow Line papers on arXiv/SSRN/ResearchGate, Kaggle/GitHub. I found **no** peer-reviewed quasi-experimental study of an Indian metro line opening on ridership. The Delhi DiD papers (Garg; Kapoor et al.; Seki & Yamada) study crime and employment outcomes, not ridership. The building blocks are all published:
- Spillovers from a new line onto existing stations: Lu 2026, Ding 2025, Park & Eom 2024, Fu 2018.
- Bus overlap as moderator: Chai 2025, Liu 2026, Gao 2022.
- Bengaluru metro–bus competition and complementarity: Hasan 2025, Gadepalli 2022, CiSTUP 2023.
- The specific Bengaluru hypothesis: Diagram Chasing 2025.

**Remaining delta:** the first station/OD-level causal estimate for an Indian line opening, with exposure built from dated open GTFS. That is a new city + new data + a known design, i.e. a solid 3. It reaches 3.5–4 only if the OD-level diversion test (below) works and a second event (Pink Line) replicates it.

### Is the DiD credible with 10 pre-days and 8 post-days? Only for a narrow estimand.
1. **The effective sample is much smaller than it looks.**
   - Pre (1–10 Aug) holds only **6 weekdays** (1, 4–8 Aug). 8 Aug was Varamahalakshmi (a Karnataka festival; verify its holiday status), 9 Aug Raksha Bandhan, and 10 Aug the inauguration Sunday with the PM's visit.
   - Post (11–18 Aug) holds **5 clean weekdays** (11–14, 18), plus I-Day and Janmashtami.
   - The hourly panel inflates N, but treatment varies only across **67 stations at one date**. The design is essentially **one cross-sectional regression of Δlog(ridership) on exposure, n = 67**. A daily event-study pre-trend test on about 6 pre-weekdays has almost no power. Reviewers will say so.
2. **Time-varying, station-specific shocks straddle the treatment date.**
   - The Lalbagh flower show ran 7/8–17/18 Aug and peaked on 15 Aug.
   - In opening week there are joyriders and novelty trips (RV Road and Majestic interchange spikes).
   - Hosur Road traffic fell about 10% ([Oneindia](https://oneindia.com/bengaluru/bengaluru-traffic-eases-as-namma-metro-yellow-line-opens-10-drop-on-hosur-road-011-7835111.html)).
   - Date×hour fixed effects absorb none of these, because they are *differential* across stations, and they are concentrated exactly where exposure is high (south and central Green Line).
3. **Exposure is confounded with geography. This is the fatal-if-ignored problem.**
   - `YellowOverlap_s`, `Collinear_s` and `MetroPathToRV_s` will all be high for the same cluster: Banashankari, JP Nagar, Jayanagar, South End, Lalbagh, Chickpete, RV Road.
   - With n = 67, the "incremental R² of bus terms over metro-only exposure" (the proposal's key result) will be unstable and possibly unidentified.
   - **Week-1 check:** compute corr(YellowOverlap, MetroPathToRV). If |r| > 0.8, the bus-mediation claim cannot be separated from metro geography in this design.
4. **The September extension does not fix the pre-period.** It adds post days only, for station entries only (no OD), after a 12-day gap. Its contrast is still against the same 6 pre-weekdays, now across months: monsoon, Ganesh Chaturthi on 27 Aug, Dasara holidays from about 20–22 Sep.
5. **Inference.** Wild-cluster bootstrap by station is fine. Randomisation inference (permuting exposure) is good. However, the proposal lists four exposures × peak/off-peak × weekday/weekend × station/OD × PPML/OLS. That garden of forking paths will draw a "specification search" objection. Pre-register one primary specification (OSF) before running the post-period models.

**Bottom line on DiD:** the design is credible for a **short-run differential response of existing stations, with continuous exposure**, presented with honest power and randomisation-inference p-values. It is **not** credible for claiming the response is *bus-mediated*, nor for any medium-run effect.

### Is a "bus-overlap score" a convincing mechanism? Not by itself.
- It measures **bus supply potential, not bus use**. No BMTC ridership is observed, so "bus-mediated" is inferred from a correlation between supply geography and metro change. A reviewer will list alternatives that produce the same correlation:
  - (a) metro-internal rerouting (Green → RV Road → Yellow replaces Green → Banashankari plus bus, which *is* your mechanism, but also Green → Majestic → … paths);
  - (b) road decongestion on Hosur Road changing auto/cab-to-metro access;
  - (c) new trips generated by curiosity;
  - (d) flower show and festival geography.
- GTFS only includes routes with live tracking, and timetables are interpolated. Trip counts at stops are *roughly* right, but overlap measured as "route stops within 800 m of a Yellow station" is crude. Validate it against a manual list of the routes that serve Banashankari/Chickpete → Silk Board/Electronic City.
- **What would make the mechanism convincing:**
  1. **A directional and time-of-day signature.** If former metro + bus commuters to Electronic City switch to the Yellow Line, bus-transfer stations should lose **AM-peak exits and PM-peak entries** (alighting to catch the bus in the morning, boarding after the bus in the evening), not uniformly. Generic shocks such as the flower show do not produce that pattern (they are midday/weekend). This is testable now with entries+exits by hour.
  2. **An OD diversion test with origin×date fixed effects.** For each origin o, flows o → {GTFS-identified bus-transfer nodes} should fall in proportion to the rise in o → {Yellow stations via RV Road}, *within the same origin*. That absorbs origin-level shocks. The bus data then enters as an **ex-ante prediction** of which destinations were transfer nodes, which can be falsified, rather than as a post-hoc moderator. About 67×66 pre-existing pairs give real power.
  3. **External bus validation.** File an RTI to BMTC for route-wise daily ETM ticket counts (Jul–Sep 2025) on routes linking Banashankari/Chickpete/JP Nagar stops to the Hosur Road corridor. Even 10–20 routes would turn the mechanism from inferred to observed.

### RQ4 (10 Sep headway cut): weak as specified
- The 6:00 am start-time change happened on the same day, so 6–7 am entries rise mechanically. Drop those hours.
- Yellow ridership was still **ramping up** about 4 weeks after opening, so a pre-trend is guaranteed. Use an ITS with a trend on 1–9 Sep (9 pre-days) and report the elasticity as descriptive.
- RV Road gate counts mix Green-only and Yellow riders.
- Expect an elasticity of about 0.2 (5–6% on +32% frequency). Fine as a sub-result; not a headline.

### RQ5 (bus supply response from GTFS diffs): risky
The Aug→Sep snapshot diff confounds real service changes with live-tracking coverage changes. Cross-check every "new route" against news (e.g., the MF-22 family launched 11 Aug) before claiming a supply response.

### Publishability
- **Reviewer objections:** pre-period too short; parallel trends untestable; exposure collinear with geography; flower-show contamination; no bus ridership; external validity of opening week; Spark is irrelevant to the transport contribution.
- **Odds (as written):** Scopus conference ~55%; CSTP / TiDE / *Findings* ~25%; JTG/TRR/TR-A ≤3%.
- **With the fixes below:** ~70% / ~45% / 10–15%. *Findings* is the best fit for one clean natural-experiment result. CSTP fits because it published Gadepalli 2022.

### Fixes, in priority order
1. **File RTIs to BMRCL in week 1** for station-pair hourly data for **July 2025** (a real 4–5-week pre-period) and **19 Aug–Oct 2025**. The requester obtained Aug and Sep this way, so the format and process are known. This single fix removes the biggest objection.
2. **Second event:** RTI for station-pair hourly data for **Oct–Dec 2026** around the **Pink Line opening (14 Nov 2026, verified)**. Two openings with the same design turn a case study into a replicated finding.
3. Make the **OD diversion test** plus the **AM-exit/PM-entry signature** the primary analysis. Make station-level continuous-exposure DiD secondary.
4. Pre-register the primary specification. Report randomisation-inference p-values. Drop Lalbagh, Mahalakshmi and Cubbon Park-adjacent stations for 7–18 Aug as a robustness block.
5. Report the exposure collinearity matrix up front. If bus and metro-geography exposure cannot be separated, claim a "reallocation consistent with bus-transfer substitution", not mediation.
6. BMTC route-ticket RTI as upside.
7. Move Spark scaling to an appendix or a separate systems paper.

---

## 4. Idea B: Feeder/competition index with new-line transfer test

### Novelty: 2/5
- Hasan et al. 2025 already find, for Bengaluru, that feeder bus routes raise and parallel routes reduce metro ridership. The ResearchGate version mentions a reciprocal feeder-line/boarding relationship.
- Lim 2025 (MIT) builds GTFS competing and complementary route variables. Deepa 2022 does it for BMTC. Metro-MGAT (2024) does new-station prediction. Kori & Srikanth 2025 build a Bengaluru integration index.
- What remains is the GTFS *angle-based* feeder/collinear decomposition and the leave-line-out test. That is incremental.

### Soundness problems
- Training n = 67 stations (cross-section; hourly profiles do not add independent stations). Spatial autocorrelation plus a GNN on 67 nodes is a recipe for overfitting, and reviewers know it.
- **The Yellow out-of-sample test is confounded by supply.** In Aug 2025 the line ran 3 trains at a 25-min headway, with one interchange and opening-week novelty. Observed ridership reflects capacity and novelty, not catchment demand. Any model trained on mature Purple/Green stations will "fail" for reasons unrelated to the bus index.
- The Pink test has 6 stations and no data in hand. Hourly data would need an RTI with an uncertain timeline. "Forecast published, evaluation pending" is not a paper.
- The feeder-gap residual ranking is a policy deliverable, not a research contribution.

### Odds
Conference ~45% (a GNN/UrbanAI workshop is possible); journal ~15%; top <3%. **Verdict: drop as standalone.** Use the feeder/collinear index as the exposure variables in A, which is where it adds value.

---

## 5. Idea C: Multilayer accessibility, bus-enabled share of Yellow Line benefit

### Novelty: 2/5
Before/after GTFS accessibility for new lines is routine (Oslo, Brussels, Bogotá, Guangzhou with Gini/Palma). Bengaluru ward-level PT equity (2022) and feeder equity (2026) exist. Shanmukhappa 2018 built Bengaluru bus+metro multilayer topology. The "bus-leg share of the gain" decomposition via a counterfactual that removes interlayer links is a modest twist; Niterói arXiv 2611.14499 does a similar component decomposition.

### Soundness
- Interpolated BMTC timetables plus a headway-based BMRCL GTFS mean that minute-level travel times are soft. Use frequency-based routing and sensitivity bands, as the proposal says.
- Validation against "observed metro OD change by ward" is weak: wards do not map cleanly to origin stations, and only 5 clean post weekdays exist.
- Population data is 2011.

### Odds
IEEE BigData/ITSC workshop ~55% if framed as a **Spark-parallel accessibility pipeline**; this is the one idea where the team's Hadoop/Spark brief is a genuine contribution. Journal ~20%; top <3%. **Verdict: pursue with changes, as the secondary systems paper only.**

---

## 6. Section 7 data paper (*Data in Brief*)
The value is real (crosswalk plus GTFS snapshot features), but there is a **licence conflict**. OpenCity labels the ridership data CC non-commercial, while GitHub is ODbL (share-alike) with "some content © BMRCL". *Data in Brief* normally expects openly licensed (CC-BY-type) data. Publish only derived features and code, and link to the sources. Get written confirmation from the data requester. Odds ~35%.

---

## 7. Single best path forward

**Run Idea A, re-scoped as A′:** "Short-run reallocation of metro OD flows after the Yellow Line opening: a diversion test using GTFS-identified bus-transfer nodes."

- **This week:**
  - File BMRCL RTIs for station-pair hourly data for **Jul 2025, 19 Aug–Oct 2025, and Oct–Dec 2026 (Pink Line)**.
  - File the optional BMTC RTI for route-wise ETM counts on Hosur-corridor routes, Jul–Sep 2025.
  - Check the bus-exposure vs metro-geography collinearity.
  - Pre-register the primary specification on OSF.
- **Analysis:**
  - **Primary:** within-origin OD diversion test plus the AM-exit/PM-entry signature at transfer stations.
  - **Secondary:** station continuous-exposure DiD with randomisation inference; flower-show stations excluded as robustness.
  - **Descriptive:** the Sep headway analysis.
- **Replication:** repeat on the Pink Line when the RTI arrives.
- **Venues:** target ***Findings*** (fast, suits one clean result) or **CSTP**. Write the Spark pipeline plus Idea C accessibility as a separate IEEE BigData-workshop/conference paper so the course's big-data requirement is met without diluting the transport paper.

Without the longer pre-period or the Pink Line replication, expect a conference paper and a coin-flip-minus at CSTP. With either one, a mid-tier journal acceptance is realistic.
