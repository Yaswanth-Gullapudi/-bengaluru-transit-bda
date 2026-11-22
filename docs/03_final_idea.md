# Final idea: Did the bus network decide who lost metro riders when the Yellow Line opened?

Built only on open datasets that can be downloaded today. No RTI is needed.

## 1. The story in plain words
Before 11 Aug 2025 there was no metro to Hosur Road or Electronic City. Many commuters bound there did this:
take the Purple/Green Line to a station such as Banashankari or Chickpete, get off, and catch a BMTC bus for the rest of the trip.

When the Yellow Line (RV Road–Bommasandra) opened on 11 Aug 2025, those commuters could stay in the metro instead: change at RV Road and ride straight to a Yellow station.
In the metro data this shows up as a change of **exit station**. The same origin stops sending people to the old bus-transfer station and starts sending them to Yellow stations.

**Which stations lose riders depends on the bus network.** The losers are the stations where BMTC buses used to complete the trip to the new corridor.
You cannot see this with metro data alone, because it doesn't show why a station mattered. Bus data alone doesn't show that metro riders moved.
That is the bus+metro combination the project wanted, now with a testable question.

**Research question:** When a new metro line opens, does the existing bus network predict how ridership is redistributed across the old metro stations?

## 2. Data (all downloadable now)
| # | Dataset | What it gives | Download |
|---|---|---|---|
| D1 | BMRCL station-pair hourly (Aug 2025) | Origin × destination × date × hour trips, 1–18 Aug 2025 (10 days before the opening, 8 days after). The enhanced file adds stations travelled, fare and revenue. | https://github.com/Vonter/bmrcl-ridership-hourly/tree/main/data (`stationpair-hourly-enhanced.parquet` / `.csv.zip`) |
| D2 | BMRCL station hourly entries | Station × date × hour boardings, 1–18 Aug **and 1–30 Sep 2025** | same repo, `station-hourly.parquet` |
| D3 | BMRCL station hourly exits | Station × date × hour alightings, 1–18 Aug 2025 | same repo, `station-hourly-exits.parquet` |
| D4 | BMTC GTFS snapshots | Every bus route, stop (with lat/lon), trip and shape. A dated snapshot from **4 Aug 2025** (before the opening) and **2 Sep 2025** (after), plus monthly snapshots to Nov 2026 | `https://github.com/Vonter/bmtc-gtfs/raw/<commit>/gtfs/bmtc.zip`, where the commit is `6077c6a902` for 2025-08-04 and `5b22150afc` for 2025-09-02. The others are listed in the repo's commit history. |
| D5 | Metro station coordinates and line geometry | Points for the 83 stations and the Yellow alignment | OpenStreetMap (Overpass query `railway=station` + `network=Namma Metro`) |
| D6 | Ward boundaries + population (optional) | For maps and equity summaries | https://github.com/suvajit/opendata/tree/master/BBMP/data |
| D7 | Your existing BMTC stops/routes-by-ward files | Cross-check against GTFS | already have |

Licence: the GitHub repos are ODbL. Cite the repos and the RTI source as their READMEs ask.

## 3. Method, step by step

### Step 1: Big-data pipeline (Spark on HDFS)
- Load D1–D4 into HDFS as parquet, partitioned by date (and by snapshot date for GTFS).
- Clean the data and harmonise station names (the repo provides name and code maps).
- Do a spatial join from metro stations to BMTC stops within 400 m and 800 m, in Spark or Apache Sedona.

### Step 2: Build the bus-link score for each old station (GTFS 4 Aug 2025, before the opening)
For each of the ~67 Purple/Green stations *s*:
- `BusTrips_s`: daily bus trips stopping within 400 m of *s*.
- `YellowLink_s`: the share of those trips on routes that **also stop within 800 m of a Yellow Line station**. This is how strongly *s* worked as a bus jump-off point toward the new corridor.
- Controls that capture plain geography: metro distance (in stations) to RV Road, line (Purple or Green), and baseline ridership.

**Freeze a list of the top-k "bus-transfer stations" by `YellowLink_s` before looking at any ridership numbers.** Post the list on OSF or GitHub with a timestamp. This makes the test a genuine prediction.

### Step 3 (main test): Origin–destination diversion (D1)
For every origin *o*, compare trips to each destination *d* before and after 11 Aug:

flow(o,d,day,hour) ~ FE[o × day × hour] + FE[o × d × hour] + β · After × YellowLink_d

- The origin × day × hour fixed effect absorbs anything that hits an origin on a given day: the Lalbagh flower show, opening-week joyriders from that origin, rain, holidays.
- The model then asks: **from the same origin, did the trip share going to bus-transfer stations fall?** Prediction: β < 0.
- **A second, falsifiable check across origins:** the origins that lost the most trips to bus-transfer stations should be the same origins that gained the most trips to Yellow stations. If the bus mechanism is wrong, these two shifts will not line up.
- Estimate with Poisson pseudo-maximum likelihood (PPML), because the counts contain many zeros.

### Step 4: Time-of-day signature (D2 + D3)
Commuters rerouting should produce a specific pattern at bus-transfer stations:
- fewer **morning-peak exits** (people no longer get off there to catch the bus);
- fewer **evening-peak entries** (people no longer come back by bus to board there).

The flower show or a festival would raise midday and weekend traffic instead. Checking which pattern appears separates the bus mechanism from these events.

### Step 5: Does the effect last? (D2, September)
- Compare September entries at bus-transfer stations with early August. This gives 30 days after the opening instead of 8.
- Drop the 6–7 am hour, because first service moved to 6:00 am on 10 Sep.
- **Extra result, descriptive only:** Yellow-station entries before and after the 10 Sep headway cut (25 → 19 min), as an approximate measure of how ridership responds to frequency.

### Step 6: How did BMTC respond? (D4, snapshot series)
- Compare the 4 Aug and 2 Sep 2025 GTFS snapshots, then the monthly snapshots up to 2026.
- Questions: Did BMTC cut trips on the old bus links from bus-transfer stations to Hosur Road? Did it add feeder routes, such as MF-22, at Yellow stations?
- This gives a supply-side event study of the bus network reacting to the metro.

### Step 7: Robustness (what reviewers will ask for)
- **Geography check:** report the correlation between `YellowLink_s` and distance to RV Road. Run the main test with the geography controls included, and within a single line.
- **Randomisation inference:** shuffle the score across stations 1,000 times. Is the real β extreme?
- **Placebo opening dates:** 5 Aug and 7 Aug should show no effect.
- **Event days:** drop 15–16 Aug (Independence Day, Janmashtami), Lalbagh station, and the first two days of joyriding.
- **Buffer size:** repeat with 400 m vs 800 m buffers.

### Step 8: Spark performance (the course requirement)
- Time Steps 1–2 and the panel build on 1, 2 and 4 executors.
- Repeat at 1×, 5× and 20× data volume by stacking the 27 GTFS snapshots and replicating the origin–destination panel.
- Report strong and weak scaling.

## 4. Expected outputs
1. Map: metro stations coloured by `YellowLink_s`, with the Yellow alignment and BMTC routes.
2. Main result: from the same origin, the trip share to bus-transfer stations before vs after the opening (event-study plot by day).
3. Scatter across origins: loss to bus-transfer stations vs gain to Yellow stations.
4. Hourly profile at bus-transfer stations: AM/PM peak dip.
5. Time series of BMTC bus trips around Yellow stations, 2024–2026.
6. Spark scaling table and plots.

## 5. Contribution claim (honest)
- This would be the first quasi-experimental analysis of an Indian metro line opening that uses the dated bus network (open GTFS) to test **why** ridership moved between old stations.
- It also documents how the bus network responded.
- Existing work stops short of this:
  - Hasan et al. 2025 (TR-A) is a single snapshot with no opening event.
  - Gadepalli et al. 2022 is descriptive and uses closed data.
  - The Diagram Chasing blog only *guessed* this mechanism, with no bus data and no test.
  - Chai, Sun & Yin 2025 (TR-A) study bus–metro overlap at city level in China.

## 6. Limits and how to state them
- **Short window (8 post-days for the OD data):** the main claim is a short-run redistribution. September extends station-level entries only.
- **No BMTC ridership data:** the bus side is measured by supply (trips and routes), not by bus riders.
- **No pure control group:** the whole network is affected. The estimand is the *differential* change explained by bus links.

## 7. Where to submit
- **Realistic on this data alone:** a Scopus-indexed conference (IEEE ITSC, IEEE BigData workshops, Springer LNCE / TPMDC) or *Findings* (short-paper format).
- **Stretch:** *Case Studies on Transport Policy* or *Transportation in Developing Economies*. Odds rise a lot if a longer before-period is obtained later via RTI. That is optional and not required for this plan.
- **Optional second paper:** the Spark pipeline and the 27-snapshot GTFS processing, written as a systems paper.

## 8. Semester plan (~12 weeks)
| Weeks | Work |
|---|---|
| 1–2 | Download D1–D5, set up HDFS + Spark, clean the data, build the station crosswalk |
| 3 | Build the bus-link score; freeze and timestamp the bus-transfer station list |
| 4–6 | Main origin–destination diversion test + cross-origin check |
| 7 | Time-of-day signature, September persistence, headway descriptive |
| 8 | BMTC supply response across GTFS snapshots |
| 9 | Robustness checks |
| 10 | Spark scaling experiments |
| 11–12 | Figures and paper writing |
