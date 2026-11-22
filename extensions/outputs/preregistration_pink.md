# Pre-registration: Pink Line bus-diversion test

- Created (UTC): 2026-11-21T17:59:41+00:00
- Event: Pink Line opening 2026-11-14 (Kalena Agrahara - Suddaguntepalya, 5 new stations)
- Rule: top 10 existing stations by PinkLink (GTFS snapshot 2026-11-09, 400 m walk catchment, 800 m straight-line corridor), excluding Jayadeva Hospital and stations whose catchment touches the corridor
- Primary test: log(1+trips_odtb) ~ FE[o x date x band] + FE[o x d x band] + post x zPinkLink_d, clustered by destination; same as the Yellow Line test
- Frozen stations: Ragigudda, Central Silk Board, Kundalahalli, Sri Sathya Sai Hospital, Nallurahalli, Lalbagh, Banashankari, Biocon Hebbagodi, Pattandur Agrahara, Huskur Road
- SHA-256: 9a434b7cde0dbbe20be9cd7922ece898422275ea6a77ec071a6f5c9e26a9357b

No Pink Line ridership was available or examined when this list was frozen. The test runs once
post-opening station-pair data (Nov-Dec 2026) is obtained by RTI.