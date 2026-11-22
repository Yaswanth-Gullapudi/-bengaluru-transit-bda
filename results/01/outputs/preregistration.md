# Pre-registration: Yellow Line opening and bus-mediated metro ridership (Team 15)

Created (UTC): 2026-11-21T12:17:03+00:00
SHA-256 of frozen list record: 2ea7ed4b7265bc008de2affb9ff20e73478763c22098f946d03488d0deaef7a9

## Hypotheses
H1 (diversion). From the same origin, trips to stations with a high bus link to the Yellow corridor
(YellowLink, BMTC GTFS 4 Aug 2025) fall after 11 Aug 2025 relative to other destinations.
H2 (matching). Origins that lose the most share to the frozen bus-transfer stations gain the most share to new Yellow stations.
H3 (time-of-day). At the frozen bus-transfer stations, AM-peak exits and PM-peak entries fall more than midday counts.

## Frozen bus-transfer stations
Rule: top 10 old stations by YellowLink (snapshot 2025-08-04, 400 m catchment, 800 m corridor), excluding RV Road and stations whose catchment touches the corridor
Stations: Lalbagh, Kundalahalli, Sri Sathya Sai Hospital, Indiranagar, Nallurahalli, Krishnarajapura, South End Circle, Benniganahalli, Pattandur Agrahara, Banashankari

## Primary specification
Data: BMRCL station-pair hourly ridership, 1-18 Aug 2025, old stations only, aggregated to
date x time band (am_peak 7-10, midday 11-15, pm_peak 16-20, other).
Model: log(1+trips[o,d,date,band]) = FE[o x date x band] + FE[o x d x band] + b * post x zYellowLink_d + e
Inference: SE clustered by destination; wild-cluster bootstrap (Webb) and randomisation inference (1,000 permutations).
Secondary: PPML on counts; binary post x transfer_d; event study by day (reference 7 Aug).

## Pre-specified robustness
Placebo opening dates 5 and 7 Aug; drop 15-16 Aug; drop Lalbagh and Mahalakshmi; drop 11-12 Aug;
controls post x MetroHopsToRV_d, post x line_d, post x BusTrips_d; within-line samples;
400 vs 800 m catchments; exposure from the 2 Sep 2025 snapshot; hourly instead of bands.
