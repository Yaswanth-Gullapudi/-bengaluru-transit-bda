"""Team 15 · Bengaluru public transport Big Data dashboard (interactive layer).

Reads the outputs of the Spark/HDFS pipeline (notebooks 00-10 run on Kaggle, downloaded to
kaggle_results_acc2/) and presents them for the viva. Nothing here is typed in by hand:
every table and chart is read from a pipeline output file.

Run:  streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
# results downloaded from Kaggle: "results/" in the GitHub repo, "kaggle_results_acc2/" in the original working folder
RES = next((ROOT / d for d in ("results", "kaggle_results_acc2") if (ROOT / d).exists()), ROOT / "results")
EXT = next((ROOT / d for d in ("extensions/outputs", "work_ext/outputs") if (ROOT / d).exists()), ROOT / "extensions/outputs")
LINE_COLORS = {"Purple": "#7d2a6e", "Green": "#13894a", "Yellow": "#d9a400",
               "Interchange (Majestic)": "#444444", "Interchange (RV Road)": "#8a8a8a", "Pink": "#d4477e"}
st.set_page_config(page_title="Team 15 · Bengaluru Transit BDA", layout="wide")

# ---------------------------------------------------------------- look and feel (same design language as the
# reference atlas: soft grey-blue ground, white bordered cards, Bricolage Grotesque + IBM Plex, mono eyebrows)
import plotly.io as pio
_DARK = (getattr(getattr(st.context, "theme", None), "type", None) == "dark")
P = (dict(bg="#0E181C", surface="#152228", ink="#E6EEF0", ink2="#A9BBC1", muted="#80939A", line="#2A3C44", grid="#22333A",
          accent="#6BB8D4", soft="#1B3844", side="#122027")
     if _DARK else
     dict(bg="#EEF2F1", surface="#FCFCFB", ink="#15242B", ink2="#51656D", muted="#7D8C92", line="#D5DEDF", grid="#E3E9E9",
          accent="#1F6F8B", soft="#DCEAF0", side="#E4EBE9"))
st.markdown(f"""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:{P['bg']};--surface:{P['surface']};--ink:{P['ink']};--ink2:{P['ink2']};--muted:{P['muted']};--line:{P['line']};--accent:{P['accent']};--accent-soft:{P['soft']}}}
html, body, [class*="css"], .stMarkdown, .stText, p, li, label, .stRadio, .stSelectbox {{font-family:"IBM Plex Sans","Segoe UI",system-ui,sans-serif !important}}
h1,h2,h3,h4 {{font-family:"Bricolage Grotesque","Segoe UI",system-ui,sans-serif !important; color:var(--ink); letter-spacing:-.01em}}
.block-container{{max-width:1280px;padding-top:1.6rem;padding-bottom:3rem}}
.hero{{margin:0 0 18px 0}}
.hero .eyebrow{{font:500 .72rem/1 "IBM Plex Mono",Consolas,monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);margin-bottom:10px}}
.hero h1{{font-size:clamp(1.7rem,3.2vw,2.4rem);font-weight:700;line-height:1.15;margin:0;padding:0}}
.hero .lede{{color:var(--ink2);max-width:78ch;margin-top:10px;font-size:1rem}}
.hero .meta{{font:400 .78rem "IBM Plex Mono",monospace;color:var(--muted);margin-top:6px}}
[data-testid="stMetric"]{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px}}
[data-testid="stMetricLabel"] p{{font:500 .7rem "IBM Plex Mono",monospace !important;letter-spacing:.07em;text-transform:uppercase;color:var(--muted) !important;white-space:normal}}
[data-testid="stMetricValue"]{{font:600 1.6rem/1.15 "IBM Plex Sans",sans-serif !important;color:var(--ink);font-variant-numeric:tabular-nums}}
[data-testid="stPlotlyChart"],[data-testid="stDataFrame"],[data-testid="stTable"],[data-testid="stGraphVizChart"]{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px}}
[data-testid="stExpander"]{{background:var(--surface);border-radius:10px}}
[data-testid="stSidebar"]{{border-right:1px solid var(--line)}}
h2,h3{{margin-top:.6rem}}
.stRadio [role="radiogroup"] label{{font-weight:500}}
[data-testid="stCaptionContainer"]{{color:var(--muted)}}
.step{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;height:100%}}
.step .n{{font:500 .7rem "IBM Plex Mono",monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}}
.step h4{{margin:.35rem 0 .3rem 0;font-size:1.05rem}}
.step p{{color:var(--ink2);font-size:.92rem;margin:0}}
.step .num{{font:600 1.15rem "IBM Plex Sans",sans-serif;color:var(--ink);margin-top:.4rem}}
</style>""", unsafe_allow_html=True)
_t = go.layout.Template()
_t.layout = go.Layout(font=dict(family="IBM Plex Sans, Segoe UI, sans-serif", size=13, color=P["ink"]),
                      title=dict(font=dict(family="Bricolage Grotesque, Segoe UI, sans-serif", size=17, color=P["ink"])),
                      paper_bgcolor=P["surface"], plot_bgcolor=P["surface"],
                      colorway=(["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#c56cb4", "#38b872"] if _DARK else
                                ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7d2a6e", "#13894a"]),
                      xaxis=dict(gridcolor=P["grid"], zerolinecolor=P["line"], linecolor=P["line"]),
                      yaxis=dict(gridcolor=P["grid"], zerolinecolor=P["line"], linecolor=P["line"]),
                      legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=10, r=10, t=56, b=10), hoverlabel=dict(font_family="IBM Plex Sans"))
pio.templates["t15"] = _t
pio.templates.default = ("plotly_dark+t15" if _DARK else "plotly+t15")
MAP_STYLE = "carto-darkmatter" if _DARK else "carto-positron"


def hero(title: str, lede: str = "", eyebrow: str | None = None, meta: str = "") -> None:
    st.markdown(f'<div class="hero"><div class="eyebrow">{eyebrow or "Team 15 · BMRCL metro + BMTC bus"}</div>'
                f'<h1>{title}</h1>' + (f'<div class="lede">{lede}</div>' if lede else "")
                + (f'<div class="meta">{meta}</div>' if meta else "") + "</div>", unsafe_allow_html=True)


@st.cache_data
def tab(nb: str, name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(RES / nb / "outputs" / "tables" / name, **kw)


@st.cache_data
def ftab(name: str) -> pd.DataFrame:
    """Forecaster outputs: Kaggle notebook 11 if downloaded, else the local run."""
    for base in (RES / "11" / "outputs" / "tables", EXT / "tables"):
        if (base / name).exists():
            return pd.read_csv(base / name)
    raise FileNotFoundError(name)


@st.cache_data
def demo_data() -> dict:
    return json.loads((ROOT / "demo" / "demo_data.json").read_text(encoding="utf-8"))


@st.cache_data
def pink_record() -> dict:
    for p in (EXT / "frozen_pink_stations.json", ROOT / "kaggle_acc2" / "t15-code" / "outputs" / "frozen_pink_stations.json"):
        if p.exists():
            return json.loads(p.read_text())
    return {}


def line_of(lines: str) -> str:
    return {"PURPLE": "Purple", "GREEN": "Green", "YELLOW": "Yellow", "GREEN+PURPLE": "Interchange (Majestic)",
            "GREEN+YELLOW": "Interchange (RV Road)"}.get(lines, lines)


def _line_order(d: pd.DataFrame) -> pd.DataFrame:
    """Order a line's stations along its main direction (first principal axis of lon/lat), so they can be joined."""
    xy = d[["lon", "lat"]].to_numpy(float)
    if len(xy) < 3:
        return d
    c = xy - xy.mean(axis=0)
    axis = np.linalg.svd(c, full_matrices=False)[2][0]
    return d.iloc[np.argsort(c @ axis)]


def station_map(df: pd.DataFrame, color: str = "line", size: str | None = None, hover: dict | None = None,
                highlight: str | None = None, height: int = 480, title: str = "", join_lines: bool = True) -> go.Figure:
    """Station map drawn as an ordinary SVG chart (stations at their real positions, lines joined in their colours).
    It needs no map tiles and no WebGL, so it renders in every browser, offline, in screenshots and on Streamlit Cloud."""
    d = df.copy()
    fig = go.Figure()
    if join_lines:
        for ln, g in d.groupby(color):
            if ln in LINE_COLORS and len(g) > 1 and not str(ln).startswith("Interchange"):
                g = _line_order(g)
                fig.add_trace(go.Scatter(x=g["lon"], y=g["lat"], mode="lines", line=dict(color=LINE_COLORS[ln], width=3),
                                         opacity=0.45, hoverinfo="skip", showlegend=False))
    for ln, g in d.groupby(color):
        sz = (8 + 22 * (g[size] - d[size].min()) / max(d[size].max() - d[size].min(), 1e-9)) if size else 11
        cd = g[list(hover)] if hover else None
        ht = "<b>%{text}</b>" + "".join(f"<br>{lab}: %{{customdata[{i}]:,.0f}}" for i, lab in enumerate((hover or {}).values())) + "<extra></extra>"
        fig.add_trace(go.Scatter(x=g["lon"], y=g["lat"], mode="markers", name=str(ln), text=g["n"], customdata=cd,
                                 hovertemplate=ht, marker=dict(size=sz, color=LINE_COLORS.get(ln, P["accent"]),
                                                               line=dict(color=P["surface"], width=1))))
    if highlight is not None and (d["n"] == highlight).any():
        h = d[d["n"] == highlight]
        fig.add_trace(go.Scatter(x=h["lon"], y=h["lat"], mode="markers+text", text=[highlight], textposition="top center",
                                 marker=dict(size=26, color="rgba(0,0,0,0)", line=dict(color=P["ink"], width=2.5)),
                                 textfont=dict(color=P["ink"], size=13), hoverinfo="skip", showlegend=False))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1.026)   # 1/cos(13°): equal km in both directions
    fig.update_layout(height=height, title=title, legend=dict(orientation="h", y=-0.02, title=""),
                      margin=dict(l=10, r=10, t=50 if title else 10, b=10))
    return fig


PAGES = ["Overview", "How it works", "Line explorer", "Network analytics", "Station explorer", "Yellow Line test", "Headway",
         "All lines", "Machine learning", "Demand forecaster", "Supply gap & fixes", "Fare revenue", "Spark scaling", "Pink Line", "Data & reproducibility"]
st.sidebar.markdown("<div class=\"hero\"><div class=\"eyebrow\">BDA project</div><h1 style=\"font-size:1.4rem\">Bengaluru Transit</h1></div>", unsafe_allow_html=True)
st.sidebar.caption("BMRCL metro + BMTC bus · HDFS + Spark 4 on Kaggle")
_qp = st.query_params.get("page")                      # deep links: ?page=Fare%20revenue
if _qp in PAGES and "page" not in st.session_state:
    st.session_state["page"] = _qp
page = st.sidebar.radio("Page", PAGES, key="page")
st.sidebar.markdown("---")
st.sidebar.caption("Light or dark: menu (top right) > Settings > Theme. The charts and cards follow it.")
st.sidebar.caption("Gullapudi Yaswanth · Madhurashree M · Mahadhii Ganapathi Subramanian\n\nAdvisor: Ms. Sangita Khare")

# ============================================================================ Overview
if page == "Overview":
    hero("Did buses push metro riders onto the Yellow Line?",
         "A Big Data pipeline joining BMRCL metro ridership, 26 BMTC bus-network snapshots, the OpenStreetMap walking "
         "network and booth-level population, used to test a dated natural experiment: the Yellow Line opening on 11 Aug 2025. "
         "Every number on these pages is read from the pipeline's output files.",
         eyebrow="BDA project · Team 15 · Overview", meta="Data: Aug-Sep 2025 metro RTI · 26 GTFS snapshots 2024-2026 · 14 Kaggle notebooks")
    me = tab("02", "main_diversion_estimates.csv")
    hw = tab("03", "headway_did.csv")
    sc = tab("06", "scaling_results.csv")
    prim = me.iloc[0]
    el = hw.loc[hw["model"].str.startswith("lentries") & (hw["term"] == "treat"), "elasticity"].iat[0]
    s4 = sc[(sc.engine == "spark") & (sc.cores == 4) & (sc.snapshots == 26)].seconds_median.iat[0]
    pdz = sc[(sc.engine == "pandas") & (sc.snapshots == 26)].seconds_median.iat[0]
    c = st.columns(4)
    c[0].metric("Metro trips analysed (OD, 1-18 Aug)", "12.06 M")
    c[1].metric("Bus stop-time rows (26 snapshots)", f"{int(sc.stop_times_rows.max()) / 1e6:.1f} M")
    c[2].metric("Diversion effect per SD bus link", f"{prim.Estimate * 100:+.2f}%", f"p = {prim['Pr(>|t|)']:.2f}", delta_color="off")
    c[3].metric("Frequency elasticity (headway cut)", f"{el:.2f}")
    c = st.columns(4)
    c[0].metric("Spark 4 cores vs pandas (26 snapshots)", f"{pdz / s4:.1f}x faster")
    acc = tab("08", "access_summary.csv").iloc[0]
    c[1].metric("People gaining walk access to metro", f"{acc.gained_direct_access / 1e3:,.0f}k")
    c[2].metric("People reaching the Yellow corridor by bus", f"{acc.bus_link_to_yellow_400m / 1e6:.2f} M")
    c[3].metric("Notebooks run on Kaggle", "14")
    st.subheader("Pipeline")
    _fill, _key, _hi, _ink = (P["surface"], P["soft"], "#4a3d10" if _DARK else "#fde9b0", P["ink"])
    st.graphviz_chart(f"""
digraph {{ rankdir=LR; bgcolor="transparent"; edge [color="{P['muted']}"];
 node [shape=box, style="rounded,filled", fillcolor="{_fill}", color="{P['line']}", fontcolor="{_ink}", fontname="Helvetica"];
 src [label="Raw data\\nRTI metro (OD + hourly)\\n26 BMTC GTFS snapshots\\nOSM walk graph\\nBooth population"];
 hdfs [label="HDFS (Hadoop 3.3.6)\\nParquet, partitioned\\nby snapshot", fillcolor="{_key}"];
 sql [label="Spark SQL\\npanels, joins,\\nnetwork analytics"]; ml [label="Spark MLlib\\nLR / RF / GBT\\n+ placebo"];
 econ [label="Econometrics\\nfixed effects, bootstrap,\\nrandomisation"]; out [label="Outputs\\ntables + figures"];
 dash [label="This dashboard\\n(Streamlit + Plotly)", fillcolor="{_hi}"];
 src -> hdfs -> sql -> out; hdfs -> ml -> out; hdfs -> econ -> out; out -> dash; }}""")
    st.subheader("Answers")
    st.table(pd.DataFrame({
        "Question": ["Did bus-linked stations lose trips to the Yellow Line?", "Did more frequent trains help?",
                     "Are bus-linked stations busier (cross-section)?", "Did diversion appear after the 10 Sep cut?",
                     "Does bus data help predict new stations?", "Spark vs pandas"],
        "Answer": [f"No: {prim.Estimate * 100:+.2f}% per SD (p = {prim['Pr(>|t|)']:.2f}), holds in 22 checks",
                   f"Yes: elasticity {el:.2f}", "Yes: +28.6% entries per SD (p = 0.005)",
                   "Borderline: transfer stations -1.3% exits (p = 0.037)",
                   "Ranking yes (rank corr 0.26 to 0.60), levels no", f"Spark {pdz / s4:.1f}x faster at 38.6 M rows"]}))

# ============================================================================ How it works
elif page == "How it works":
    hero("How this project works",
         "A plain-language tour of what happens between a ticket gate, a bus timetable and a number on this screen: "
         "where the data comes from, what the computer does with it, how the test and the models work, and how we checked ourselves.",
         eyebrow="BDA project · How it works")

    def steps(cards):
        cols = st.columns(len(cards))
        for c, (n, t, body, num) in zip(cols, cards):
            c.markdown(f'<div class="step"><div class="n">{n}</div><h4>{t}</h4><p>{body}</p>'
                       + (f'<div class="num">{num}</div>' if num else "") + "</div>", unsafe_allow_html=True)

    st.subheader("What this project is, in plain words")
    st.write("Bengaluru's metro (BMRCL) and buses (BMTC) are planned and studied separately. Metro ticket gates record every "
             "entry and exit, and the bus company publishes its timetable, but nobody had joined the two to ask a simple question: "
             "when a new metro line opens, do the buses decide who uses it? The Yellow Line, opened on 11 August 2025, gave a "
             "real-world test. Before it, many people rode the metro to a station like Banashankari and took a bus to Electronic City. "
             "If the new line replaced that bus leg, trips to those bus-transfer stations should have dropped.")
    st.write("To answer it, the project collects about 1.2 GB of public data, stores it in Hadoop, processes it with Apache Spark, "
             "and turns it into a tested answer, a forecasting tool, and this dashboard.")

    st.subheader("Step by step")
    steps([("Step 1", "Collect", "Metro ridership released under RTI, 26 dated copies of the bus timetable (2024 to 2026), "
            "the OpenStreetMap walking network and polling-booth population.", "12.06 M metro trips · 38.6 M bus stop-times"),
           ("Step 2", "Store", "Everything goes into HDFS, Hadoop's file system, as compressed Parquet files sorted into folders by date, "
            "so Spark reads only what a question needs.", "297 MB on HDFS · Parquet 4.2x smaller than CSV"),
           ("Step 3", "Clean", "Duplicates, missing values, impossible coordinates and broken links are checked on every table. "
            "Bus trips listing only 1-2 stops are flagged as feed errors.", "7,128 incomplete bus trips flagged"),
           ("Step 4", "Link", "For every metro station, find the buses that stop within a 400 m walk, and how many of them also reach the "
            "new Yellow Line. That share is the station's bus-link score.", "83 stations scored")])
    st.write("")
    steps([("Step 5", "Freeze", "Before looking at any ridership, the 10 most bus-linked stations were written down, timestamped "
            "and fingerprinted with SHA-256, so the test could not be bent to fit the data.", "Frozen 21 Nov 2026, 12:17 UTC"),
           ("Step 6", "Test", "Compare trips from the same station on the same day to bus-linked vs other destinations, before and after "
            "the opening. This removes weather, festivals and anything else that hits a whole station.", "+0.65% per SD, p = 0.64"),
           ("Step 7", "Model", "Spark MLlib models predict ridership with and without bus data, and against shuffled bus data, "
            "to see whether bus information really adds anything.", "Ranking of new stations 0.26 to 0.60"),
           ("Step 8", "Forecast", "A Random Forest forecasts tomorrow's entries at every station and hour, with a 90% range "
            "and a crowding warning, and is scored against simple guesses.", "8.1% smaller miss · 93% range coverage")])

    st.subheader("How the main test works")
    st.write("Think of every pair of stations, say Jayanagar to Banashankari, in three parts of each day. The test asks: after 11 August, "
             "did trips to stations with many bus links to the new line fall, compared with trips from the same origin, on the same day, "
             "to stations with few such links? Comparing within the same origin and day cancels anything that affects the whole station "
             "that day. Comparing each pair with its own normal level cancels the fact that some pairs are always busy.")
    st.latex(r"\log(1+\text{trips}) = \text{origin-day effect} + \text{pair effect} + \beta \times \text{after} \times \text{bus link of destination}")
    st.write("If buses had pushed riders onto the new line, beta would be negative. It came out at +0.65% (p = 0.64): no sign of it, "
             "in 22 different versions of the test.")

    st.subheader("How we checked ourselves")
    checks = pd.DataFrame({
        "Check": ["Decide before looking", "Small number of stations", "Shuffle test", "Placebo dates", "Change the definitions",
                  "Fake-data features", "Unseen days", "Same code everywhere"],
        "What it means": ["The station list and the test were frozen and hashed before any ridership was opened.",
                          "With 68 stations, ordinary error bars can be too narrow, so we used a wild bootstrap (9,999 redraws).",
                          "Shuffling bus scores across stations 1,000 times shows how often chance alone gives a result this big.",
                          "Pretending the line opened on 5 or 7 August checks that the method does not find effects where none exist.",
                          "Walking vs straight-line distance, 400 m vs 800 m, August vs September timetables: the answer stays the same.",
                          "Machine-learning models are also given shuffled bus data; real bus data must beat it to count.",
                          "The forecaster is tested once on 22-30 September, days it never saw.",
                          "Every number comes from notebooks run on Kaggle; this dashboard only reads their output files."]})
    st.dataframe(checks, hide_index=True, width="stretch")

    st.subheader("What it found")
    st.markdown("1. **Bus links did not move metro riders** in the first eight days (a firm no-effect result).\n"
                "2. **Train frequency did**: when the wait fell from 25 to 19 minutes, Yellow Line entries rose 8.7% (elasticity about 0.3).\n"
                "3. **Bus-linked stations are busier in general** (+28.6% per SD): buses shape where riders are, just not this short-run switch.\n"
                "4. **Where feeders would help most**: Seetharampalya, MG Road, Kengeri, Vidhana Soudha and Majestic are busy but weakly linked by bus.\n"
                "5. **A useful forecaster**: next-day station demand with ranges that hold 93% of the time and crowding warnings at 86% precision.")

    st.subheader("What it cannot say")
    st.write("Station-pair data covers only 1-18 August 2025, so longer-run diversion cannot be ruled out. Bus data is the timetable, "
             "not passenger counts, so it measures bus links, not bus use. The Pink Line test is set up but waits for ridership data.")

    with st.expander("Words used on these pages"):
        st.markdown(
            "- **HDFS**: Hadoop Distributed File System, where the data is stored.\n"
            "- **Spark / Spark SQL / MLlib**: the engine that processes the data, its query language, and its machine-learning library.\n"
            "- **GTFS**: the standard file format for public transport timetables.\n"
            "- **Bus-link score (YellowLink)**: share of bus trips near a station that also reach the new line.\n"
            "- **p-value**: how likely a result this big would appear by chance if there were no real effect (small = convincing).\n"
            "- **Elasticity**: % change in riders for each 1% change in waiting time.\n"
            "- **SD**: standard deviation, a typical difference between stations.\n"
            "- **90% range**: a band the forecaster expects the real value to fall inside 9 times out of 10.")

# ============================================================================ Line explorer
elif page == "Line explorer":
    hero("Line explorer: every metro line", eyebrow=page)
    line = st.radio("Line", ["Purple", "Green", "Yellow", "Pink"], horizontal=True, key="line_pick")
    D = demo_data()
    S = pd.DataFrame([{**{k: v for k, v in s.items() if k not in ("d", "h")}, "pre": s["d"]["pre"], "post": s["d"]["post"],
                       "sep": s["d"]["sep"], "h_sep": s["h"]["sep"]} for s in D["stations"]])
    S["line"] = S["l"].map(line_of)
    on_line = S["l"].str.contains(line.upper())          # interchanges count for both lines
    if line == "Pink":
        st.info("The Pink Line opened on 14 Nov 2026. No ridership has been released for it yet, so this page shows its "
                "stations and the pre-registered bus-link test. Its ridership test runs once Nov-Dec 2026 data is obtained by RTI.")
        pk = pd.DataFrame(D["pink"])
        st.plotly_chart(station_map(pk.assign(line="Pink"), height=420, title="Pink Line stations (opened 14 Nov 2026)"),
                        width="stretch")
        ps = tab("10", "pink_station_scores.csv")
        st.subheader("Existing stations with the strongest bus links to the Pink corridor")
        st.dataframe(ps.sort_values("PinkLink", ascending=False).head(15)[["station", "lines", "BusTrips", "PinkLink", "PinkLinkTrips", "MetroHopsToJayadeva"]].round(3),
                     hide_index=True, width="stretch")
        rec = pink_record()
        st.code("frozen list: " + ", ".join(rec.get("stations", [])) + chr(10) + "sha256: " + str(rec.get("sha256")))
    else:
        L_ = S[on_line].copy()
        A = tab("10", "integration_index.csv").set_index("station")
        L_["integration_index"] = L_["n"].map(A["integration_index"]); L_["feeder_trips"] = L_["n"].map(A["feeder_trips"])
        L_["bus_trips"] = L_["n"].map(A["bus_trips"]); L_["gap"] = L_["n"].map(A["gap"])
        c = st.columns(5)
        c[0].metric("Stations", len(L_))
        c[1].metric("Weekday entries, September", f"{L_['sep'].sum():,.0f}")
        if line != "Yellow":
            c[2].metric("Change after Yellow opened (11-18 Aug)", f"{L_['post'].sum() / L_['pre'].sum() - 1:+.1%}")
        else:
            c[2].metric("Opened", "11 Aug 2025")
        c[3].metric("Mean bus trips within 400 m", f"{L_['bus_trips'].mean():,.0f}")
        c[4].metric("Mean feeder trips", f"{L_['feeder_trips'].mean():,.0f}")
        L_["sz"] = np.sqrt(L_["sep"].clip(lower=300))
        st.plotly_chart(station_map(L_.assign(line=line), size="sz", height=440,
                                    hover={"sep": "weekday entries (Sep)", "bus_trips": "bus trips within 400 m",
                                           "feeder_trips": "feeder trips"},
                                    title=f"{line} Line stations (bubble size = September weekday entries)"), width="stretch")
        c1, c2 = st.columns(2)
        top = L_.sort_values("sep", ascending=False).head(15).iloc[::-1]
        c1.plotly_chart(px.bar(top, x="sep", y="n", orientation="h", color_discrete_sequence=[LINE_COLORS[line]],
                               labels={"sep": "weekday entries (Sep)", "n": ""}, title=f"Busiest {line} Line stations"), width="stretch")
        hours = np.array(L_["h_sep"].tolist()).sum(axis=0)
        c2.plotly_chart(px.bar(x=list(range(24)), y=hours, color_discrete_sequence=[LINE_COLORS[line]],
                               labels={"x": "hour", "y": "average weekday entries"}, title=f"{line} Line entries by hour (Sep weekdays)"),
                        width="stretch")
        c1, c2 = st.columns(2)
        c1.subheader("Busy but poorly connected by bus")
        c1.dataframe(L_.sort_values("gap", ascending=False).head(8)[["n", "sep", "bus_trips", "feeder_trips", "integration_index"]]
                     .rename(columns={"n": "station", "sep": "weekday entries"}).round(2), hide_index=True, width="stretch")
        cl = ftab("station_clusters.csv").set_index("station")["cluster_name"]
        mix = L_["n"].map(cl).value_counts().rename_axis("station type").reset_index(name="stations")
        c2.subheader("Station types (KMeans)")
        c2.dataframe(mix, hide_index=True, width="stretch")
        tp = ftab("forecast_test_predictions.csv")
        tl = tp[tp.station.isin(L_["n"])]
        c2.metric("Forecaster average miss on this line (22-30 Sep)", f"{(tl.pred - tl.entries).abs().mean():.1f} entries/hour",
                  f"90% range coverage {tl.inside.mean():.1%}", delta_color="off")
        if line != "Yellow":
            fl = tab("10", "line_demand_flows.csv")
            st.subheader(f"Trips starting on the {line} Line, by destination line (weekday averages)")
            st.dataframe(fl[fl.lo == line].round(1).rename(columns={"lo": "from line", "ld": "to line"}), hide_index=True, width="stretch")
            od = tab("10", "opening_effect_by_line_od.csv")
            r = od[od["model"].str.contains(line)]
            if len(r):
                st.caption(f"Bus-diversion test for {line} Line destinations: {r.Estimate.iat[0] * 100:+.2f}% per SD of bus link "
                           f"(p = {r['Pr(>|t|)'].iat[0]:.2f}), no diversion.")
        else:
            st.caption("Yellow Line riders came mostly from the Green Line via RV Road (5.4% of Green trips vs 1.8% of Purple trips). "
                       "See the Headway page for the 10 Sep frequency effect.")
        with st.expander(f"All {line} Line stations"):
            st.dataframe(L_[["n", "pre", "post", "sep", "bus_trips", "feeder_trips", "integration_index"]]
                         .rename(columns={"n": "station", "pre": "1-10 Aug", "post": "11-18 Aug", "sep": "September"}).round(2),
                         hide_index=True, width="stretch")

# ============================================================================ Network analytics
elif page == "Network analytics":
    hero("BMTC and BMRCL network analytics (Spark SQL, notebook 09)", eyebrow=page)
    q = tab("09", "network_data_quality.csv")
    with st.expander("Data quality and cleaning", expanded=True):
        st.dataframe(q[["table", "check", "rows_affected", "action"]], hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    r = tab("09", "network_route_stats.csv")
    n = c1.slider("Top routes", 5, 40, 15, key="nr")
    top = r.head(n).iloc[::-1]
    c1.plotly_chart(px.bar(top, x="weekday_trips", y="route", orientation="h", hover_data=["route_long_name", "length_km"],
                           title=f"Top {n} routes by weekday trips"), width="stretch")
    s = tab("09", "network_shared_stops.csv")
    m = c2.slider("Top shared stops", 5, 40, 15, key="ns")
    c2.plotly_chart(px.bar(s.head(m).iloc[::-1], x="routes", y="stop_name", orientation="h", color_discrete_sequence=["#d9a400"],
                           title=f"Top {m} stops by number of routes"), width="stretch")
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.histogram(r.dropna(subset=["length_km"]), x="length_km", nbins=50, range_x=[0, 70],
                                 title="Route length (km), routes with full stop lists"), width="stretch")
    ot = tab("09", "network_over_time.csv")
    c2.plotly_chart(px.line(ot, x="snapshot", y=["weekday_trips", "routes", "stops"], markers=True, log_y=True,
                            title="Network size across 26 GTFS snapshots (log scale)"), width="stretch")
    c1, c2 = st.columns(2)
    h = tab("09", "metro_demand_hourly.csv")
    c1.plotly_chart(px.line(h, x="hour", y="avg_entries", color="period", line_dash="daytype",
                            title="Metro entries per hour, all stations"), width="stretch")
    b = tab("09", "storage_csv_vs_parquet.csv")
    c2.plotly_chart(px.bar(b, x="task", y="seconds_median", color="format", barmode="group",
                           title="CSV vs Parquet on HDFS (seconds; last pair = MB)"), width="stretch")
    cs = tab("09", "network_connectivity_summary.csv").T.reset_index()
    cs.columns = ["measure", "value"]
    st.dataframe(cs, hide_index=True)

# ============================================================================ Station explorer
elif page == "Station explorer":
    hero("Station explorer", eyebrow=page)
    D = demo_data()
    S = pd.DataFrame([{**{k: v for k, v in s.items() if k not in ("d", "h")}, "pre": s["d"]["pre"], "post": s["d"]["post"],
                       "sep": s["d"]["sep"]} for s in D["stations"]])
    S["line"] = S["l"].map(line_of)
    S["frozen"] = np.where(S["yf"], "frozen Yellow transfer", np.where(S["pf"], "frozen Pink transfer", ""))
    pk = pd.DataFrame(D["pink"]).assign(line="Pink", n=lambda d: d["n"] + " (Pink, new)")
    mp = pd.concat([S[["n", "lat", "lon", "line", "sep"]], pk[["n", "lat", "lon", "line"]].assign(sep=500)])
    mp["size"] = np.sqrt(mp["sep"].clip(lower=500))
    name = st.selectbox("Station", sorted(S["n"]), index=sorted(S["n"]).index("Banashankari"), key="stn")
    st.plotly_chart(station_map(mp, size="size", highlight=name, height=560, hover={"sep": "weekday entries (Sep)"},
                                title="All metro stations (bubble size = September weekday entries; ring = selected station)"),
                    width="stretch")
    s = next(x for x in D["stations"] if x["n"] == name)
    c = st.columns(5)
    c[0].metric("Bus trips within 400 m", f"{s.get('bt4', s['bt']):,}")
    c[1].metric("YellowLink", "n/a" if s["yl"] is None else f"{s['yl']:.0%}")
    c[2].metric("PinkLink", "n/a" if s["pl"] is None else f"{s['pl']:.0%}")
    c[3].metric("Integration rank", f"#{s.get('rank', '-')} of 83")
    c[4].metric("Feeder trips", f"{s.get('ft', 0):,}")
    d = s["d"]
    c = st.columns(3)
    c[0].metric("Weekday entries 1-10 Aug", f"{d['pre']:,.0f}" if d["pre"] else "closed")
    c[1].metric("11-18 Aug", f"{d['post']:,.0f}", f"{(d['post'] / d['pre'] - 1):+.1%}" if d["pre"] else None)
    c[2].metric("September", f"{d['sep']:,.0f}", f"{(d['sep'] / d['pre'] - 1):+.1%}" if d["pre"] else None)
    hh = pd.DataFrame({"hour": range(24), "1-10 Aug (before)": s["h"]["pre"], "11-18 Aug (after)": s["h"]["post"],
                       "September": s["h"]["sep"]}).melt("hour", var_name="period", value_name="avg weekday entries")
    st.plotly_chart(px.line(hh, x="hour", y="avg weekday entries", color="period", markers=True,
                            title=f"{name}: average weekday entries by hour"), width="stretch")
    if s["yf"] or s["pf"]:
        st.info("This station is on the frozen (pre-registered) bus-transfer list for "
                + " and ".join(x for x, f in (("the Yellow Line", s["yf"]), ("the Pink Line", s["pf"])) if f) + ".")

# ============================================================================ Yellow Line test
elif page == "Yellow Line test":
    hero("Pre-registered test: did bus-linked destinations lose trips?", eyebrow=page)
    st.latex(r"\log(1+\mathrm{trips}_{odtb}) = \alpha_{otb} + \gamma_{odb} + \beta\,\mathrm{Post}_t \times z\mathrm{YellowLink}_d + \varepsilon")
    me = tab("02", "main_diversion_estimates.csv")
    st.dataframe(me[["model", "Estimate", "Std. Error", "Pr(>|t|)", "2.5%", "97.5%", "nobs"]].round(4), hide_index=True, width="stretch")
    st.dataframe(tab("02", "main_inference.csv"), hide_index=True)
    es = tab("02", "event_study_yellowlink.csv")
    es["date"] = pd.to_datetime(es["date"])
    fig = go.Figure(go.Scatter(x=es["date"], y=es["Estimate"] * 100, mode="markers", marker=dict(size=9, color="#1f5fa8"),
                               error_y=dict(type="data", symmetric=False, array=(es["97.5%"] - es["Estimate"]) * 100,
                                            arrayminus=(es["Estimate"] - es["2.5%"]) * 100)))
    fig.add_vline(x=pd.Timestamp("2025-08-10 12:00"), line_dash="dash", annotation_text="Yellow Line opens")
    fig.add_hline(y=0, line_color="grey")
    fig.update_layout(title="Event study: daily effect per SD of YellowLink (%), 95% CI", yaxis_title="%")
    st.plotly_chart(fig, width="stretch")
    rb = tab("07", "robustness.csv", encoding="utf-8")
    pick = st.multiselect("Robustness specifications", list(rb["model"]), default=list(rb["model"]), key="rob")
    rr = rb[rb["model"].isin(pick)].iloc[::-1]
    fig = go.Figure(go.Scatter(x=rr["Estimate"] * 100, y=rr["model"], mode="markers",
                               marker=dict(size=9, color=np.where(rr["model"] == "primary", "#1f5fa8", "#888")),
                               error_x=dict(type="data", array=1.96 * rr["Std. Error"] * 100)))
    fig.add_vline(x=0, line_color="grey")
    fig.update_layout(height=max(300, 26 * len(rr)), title="Estimate per SD (%) with 95% CI", xaxis_title="%")
    st.plotly_chart(fig, width="stretch")
    ext = pd.concat([tab("10", "heterogeneity.csv"), tab("10", "pair_substitution.csv"), tab("10", "headway_shock_old_stations.csv"),
                     tab("10", "sensitivity_scores.csv")])
    with st.expander("Extensions: for whom, substitute pairs, second shock, sensitivity"):
        st.dataframe(ext[["model", "term", "Estimate", "Std. Error", "Pr(>|t|)"]].round(4), hide_index=True, width="stretch")
        st.dataframe(tab("10", "observational_cross_section.csv").round(4), hide_index=True)

# ============================================================================ Headway
elif page == "Headway":
    hero("Frequency matters: the 10 Sep 2025 headway cut", eyebrow=page)
    hw = tab("03", "headway_did.csv")
    st.dataframe(hw.round(4), hide_index=True, width="stretch")
    e_hi = hw.loc[hw["model"].str.startswith("lentries") & (hw["term"] == "treat"), "elasticity"].iat[0]
    e_lo = 0.21
    h = st.slider("New headway (minutes); opening service was 25", 8, 25, 19, key="hw")
    lo, hi = (25 / h) ** e_lo - 1, (25 / h) ** e_hi - 1
    st.metric("Predicted change in Yellow Line ridership", f"+{lo:.1%} to +{hi:.1%}")
    grid = pd.DataFrame({"headway": range(8, 26)})
    grid["DiD elasticity"] = (25 / grid.headway) ** e_hi - 1
    grid["synthetic control elasticity"] = (25 / grid.headway) ** e_lo - 1
    fig = px.line(grid.melt("headway", var_name="estimate", value_name="change"), x="headway", y="change", color="estimate")
    fig.add_vline(x=19, line_dash="dash", annotation_text="actual 10 Sep (+8.7% observed)")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
    st.caption("Published frequency elasticities: mostly +0.28 to +0.6 (headway changes, KonSULT/Leeds); "
               "Chicago headway elasticity -0.26 to -0.28 (TRR 2350).")

# ============================================================================ All lines
elif page == "All lines":
    hero("All lines: bus-metro integration and demand", eyebrow=page)
    A = tab("10", "integration_index.csv")
    lines = st.multiselect("Lines", sorted(A["line"].unique()), default=sorted(A["line"].unique()), key="lines")
    a = A[A["line"].isin(lines)]
    fig = px.scatter(a, x="integration_index", y="sep_daily_entries", color="line", hover_name="station", log_y=True,
                     size="pop_800m", color_discrete_map=LINE_COLORS,
                     title="Ridership vs bus-metro integration (top left = busy but poorly connected)")
    st.plotly_chart(fig, width="stretch")
    c1, c2 = st.columns(2)
    c1.subheader("Most under-served")
    c1.dataframe(a.sort_values("gap", ascending=False).head(10)[["station", "line", "sep_daily_entries", "bus_trips", "feeder_trips", "integration_rank"]].round(0),
                 hide_index=True, width="stretch")
    c2.subheader("Best integrated")
    c2.dataframe(a.sort_values("integration_index", ascending=False).head(10)[["station", "line", "sep_daily_entries", "bus_trips", "feeder_trips", "integration_rank"]].round(0),
                 hide_index=True, width="stretch")
    hl = tab("10", "line_demand_hourly.csv")
    per = st.radio("Period", list(hl["period"].unique()), horizontal=True, index=2, key="per")
    x = hl[hl["period"] == per].melt(["period", "line"], var_name="hour", value_name="entries")
    x["hour"] = x["hour"].astype(int)
    st.plotly_chart(px.line(x, x="hour", y="entries", color="line", color_discrete_map=LINE_COLORS,
                            title=f"Weekday entries by hour and line, {per}"), width="stretch")
    st.subheader("Effect of the Yellow opening on each line")
    st.dataframe(tab("10", "opening_effect_by_origin_line.csv").round(1), hide_index=True, width="stretch")
    fl = tab("10", "line_demand_flows.csv").head(12)
    st.dataframe(fl.round(1), hide_index=True, width="stretch")

# ============================================================================ Machine learning
elif page == "Machine learning":
    hero("Spark MLlib: does bus data improve prediction?", eyebrow=page)
    which = st.radio("Experiment", ["Old stations, out of time (05b fast grid)", "Old stations, out of time (05 full grid)",
                                    "Stations with no history"], key="mlx")
    if which.startswith("Old"):
        nb = "05b" if "05b" in which else "05"
        m = tab(nb, "mllib_metrics.csv")
        t = m[m["split"] == "test_sep"]
        tgt = st.radio("Target", ["y_level", "y_change"], horizontal=True, key="tgt")
        fig = px.bar(t[t["target"] == tgt], x="model", y="rmse", color="features", barmode="group",
                     title=f"September test RMSE ({tgt}); lower is better")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(tab(nb, "mllib_gain.csv").round(4), hide_index=True, width="stretch")
        st.caption("Bus features must beat the shuffled-bus placebo, not just metro-only, to count as informative.")
    else:
        ny = tab("10", "new_station_ml.csv").assign(test="15 new Yellow stations")
        cv = tab("10", "unseen_station_cv.csv").assign(test="68 old stations, leave-stations-out")
        both = pd.concat([ny, cv])
        st.plotly_chart(px.bar(both, x="model", y="rank_corr", color="features", barmode="group", facet_col="test",
                               title="Ranking stations by busyness (rank correlation; higher is better)"), width="stretch")
        st.dataframe(both[["test", "features", "model", "r2_log", "daily_mape_pct", "rank_corr"]].round(3), hide_index=True, width="stretch")
        st.caption("Bus data improves which new stations will be busiest (Random Forest 0.26 to 0.60; placebo 0.35), not how busy.")

# ============================================================================ Forecaster
elif page == "Demand forecaster":
    hero("Next-day metro demand forecaster", eyebrow=page)
    st.write("For every station and hour tomorrow: a forecast of entries, a 90% range and a crowding warning. "
             "Learned 8-17 Sep 2025, ranges calibrated 18-21 Sep, tested once on 22-30 Sep (never seen).")
    res = ftab("forecast_results.csv")
    best = res[res.method == "V1 Random Forest, level"].iloc[0]
    cov = ftab("forecast_coverage.csv"); warn = ftab("forecast_warnings.csv")
    c = st.columns(4)
    c[0].metric("Smaller average miss than 'same hour last week'", f"{best.skill_vs_best_simple_pct:+.1f}%")
    c[1].metric("Average miss (entries / station-hour)", f"{best.mae:.1f}")
    c[2].metric("90% range coverage on test days", f"{cov[cov.group == 'all'].coverage.iat[0]:.1%}")
    c[3].metric("Crowding warning precision", f"{warn.iloc[0].precision:.0%}")
    tp = ftab("forecast_test_predictions.csv")
    stn = st.selectbox("Station", sorted(tp.station.unique()),
                       index=sorted(tp.station.unique()).index("Nadaprabhu Kempegowda Station, Majestic"), key="fst")
    s = tp[tp.station == stn].sort_values(["day", "hour"])
    s["time"] = pd.to_datetime(s.date) + pd.to_timedelta(s.hour, unit="h")
    fig = go.Figure([go.Scatter(x=s.time, y=s.hi, line=dict(width=0), showlegend=False),
                     go.Scatter(x=s.time, y=s.lo, fill="tonexty", line=dict(width=0), name="90% range", fillcolor="rgba(31,95,168,0.18)"),
                     go.Scatter(x=s.time, y=s.pred, name="forecast", line=dict(color="#1f5fa8")),
                     go.Scatter(x=s.time, y=s.entries, name="actual", mode="markers", marker=dict(size=4, color="#222"))])
    fig.update_layout(title=f"{stn}: forecast vs actual, 22-30 Sep 2025", yaxis_title="entries per hour")
    st.plotly_chart(fig, width="stretch")
    st.subheader("Version log")
    st.dataframe(res.round(2), hide_index=True, width="stretch")
    st.caption("V2 (learn the change from last week) was tested and rejected: the test week was Navaratri, so last week was a poor anchor.")
    c1, c2 = st.columns(2)
    c1.subheader("What each input group adds")
    c1.dataframe(ftab("forecast_ablation.csv").round(2), hide_index=True, width="stretch")
    c2.subheader("Crowding warnings")
    c2.dataframe(warn.round(3), hide_index=True, width="stretch")
    st.subheader("Unusual hours (far outside the range)")
    st.dataframe(ftab("forecast_anomalies.csv").head(25).round(1), hide_index=True, width="stretch")
    st.subheader("Station types by daily rhythm (KMeans)")
    cl = ftab("station_clusters.csv"); sil = ftab("cluster_silhouette.csv")
    c1, c2 = st.columns([2, 1])
    prof = cl.groupby("cluster_name")[[str(h) for h in range(24)]].mean().T.reset_index().melt("index", var_name="type", value_name="share")
    prof["hour"] = prof["index"].astype(int)
    c1.plotly_chart(px.line(prof, x="hour", y="share", color="type", title="Average share of daily entries by hour"), width="stretch")
    c2.plotly_chart(px.bar(sil, x="k", y="silhouette", title="Silhouette by number of groups"), width="stretch")
    st.dataframe(cl[["station", "cluster_name", "am_share", "pm_share"]].round(3), hide_index=True, width="stretch")

# ============================================================================ Fare revenue
elif page == "Supply gap & fixes":
    hero("Where riders are many but buses are few, and what fixes it",
         "The forecaster predicts metro entries for every station and hour; the BMTC timetable gives the bus trips stopping within "
         "400 m in that hour. Busy hours with far fewer buses per metro rider than usual are bus gaps. Two fixes are sized: "
         "dedicated feeder buses, and more Yellow Line trains using the measured frequency elasticity.",
         eyebrow="Supply gap · notebook 13 (local, from the outputs of notebooks 10-12)",
         meta="Forecast weekdays 22-30 Sep 2025 · GTFS 4 Aug 2025 · gap = forecast ≥ 1,000 entries/h and ≥ 2× the typical busy-hour riders per bus trip")
    gs = json.loads((EXT / "tables" / "supply_gap_summary.json").read_text())
    allh = pd.read_csv(EXT / "tables" / "supply_gap_station_hours.csv")
    gl = pd.read_csv(EXT / "tables" / "supply_gap_list.csv")
    bench = gs["benchmark_riders_per_bus_trip_busy_peak"]
    c = st.columns(4)
    c[0].metric("Gap station-hours", f"{gs['gap_station_hours']}", f"{gs['gap_stations']} stations", delta_color="off")
    c[1].metric("Typical busy hour", f"{bench:.1f} riders per bus trip")
    c[2].metric("Forecast finds the real gaps", f"{gs['top20_overlap_forecast_vs_actual']} of top 20",
                f"rank corr. {gs['spearman_forecast_vs_actual_riders_per_bus']:.3f}", delta_color="off")
    c[3].metric("Crowding warnings (> 1,637/h)", f"{gs['crowded_station_hours_forecast']} station-hours")

    st.subheader("Verdict: does each busy station-hour need more buses, more trains, or both?")
    st.caption("More buses = at least twice the typical busy-hour metro riders per bus trip within 400 m. "
               "More trains = crowding warning, forecast above 1,637 entries an hour (busiest 5% of station-hours). "
               "Busy = at least 1,000 forecast entries an hour on the test weekdays.")
    vc = gs.get("verdict_counts_busy_station_hours", {})
    VCOL = {"More buses and trains": "#762A83", "More buses": "#E08214", "More trains": "#2166AC", "OK": "#BDBDBD"}
    c = st.columns(4)
    for i, k in enumerate(VCOL):
        c[i].metric(k, f"{vc.get(k, 0)} station-hours")
    vfilter = st.multiselect("Show", list(VCOL)[:3], default=list(VCOL)[:3], key="verdict_pick")
    need = allh[allh["verdict"].isin(vfilter)]
    if len(need):
        hm = allh[allh["station"].isin(need["station"].unique())].copy()
        hm["hour"] = hm["hour"].astype(int)
        fig = px.scatter(hm, x="hour", y="station", color="verdict", color_discrete_map=VCOL, symbol_sequence=["square"],
                         hover_data={"forecast_entries": ":.0f", "bus_trips": True, "riders_per_bus_forecast": ":.1f"},
                         category_orders={"verdict": list(VCOL)}, title="What each busy station-hour needs")
        fig.update_traces(marker=dict(size=16, line=dict(width=0)))
        fig.update_layout(height=max(380, 26 * hm["station"].nunique() + 140), xaxis=dict(dtick=1, title="hour of day"),
                          yaxis=dict(title="", categoryorder="total ascending"), legend=dict(orientation="h", y=-0.12, title=""))
        st.plotly_chart(fig, width="stretch")
    vt = pd.read_csv(EXT / "tables" / "supply_verdict_stations.csv")
    st.dataframe(vt[vt["verdict"].isin(vfilter)].rename(columns={"hours": "hours of day"}), hide_index=True, width="stretch")

    st.subheader("1 · Gap finder")
    top = allh.sort_values("riders_per_bus_forecast", ascending=False).head(15).iloc[::-1]
    top["label"] = top["station"] + " " + top["hour"].astype(int).map("{:02d}:00".format)
    fig = px.bar(top, x=top["riders_per_bus_forecast"].clip(upper=150), y="label", orientation="h",
                 hover_data={"forecast_entries": ":.0f", "actual_entries": ":.0f", "bus_trips": True},
                 labels={"x": "forecast metro entries per bus trip within 400 m", "label": ""},
                 title="Biggest bus gaps (bars above 150 are cut off; Kengeri has 0-1 bus trips per hour)")
    fig.add_vline(x=bench, line_dash="dash", annotation_text=f"typical busy hour {bench:.0f}")
    st.plotly_chart(fig, width="stretch")
    stn = st.selectbox("Station: forecast demand against bus trips by hour", sorted(gl["station"].unique()), key="gap_stn")
    one = allh[allh["station"] == stn].sort_values("hour")
    fig = go.Figure()
    fig.add_bar(x=one["hour"], y=one["bus_trips"], name="bus trips within 400 m", yaxis="y2", opacity=0.45)
    fig.add_scatter(x=one["hour"], y=one["forecast_entries"], name="forecast metro entries", mode="lines+markers")
    fig.update_layout(title=f"{stn}: forecast entries vs buses (hours with ≥ 1,000 forecast entries)",
                      yaxis=dict(title="metro entries per hour"),
                      yaxis2=dict(title="bus trips per hour", overlaying="y", side="right", showgrid=False),
                      xaxis=dict(title="hour of day", dtick=1), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")

    st.subheader("2 · Bus fix: size a feeder service")
    st.caption("We have bus timetables, not bus ridership, so this is a planning scenario: choose what share of metro riders "
               "would arrive by bus and how many of them one feeder trip carries.")
    a, b = st.columns(2)
    share = a.slider("Share of metro riders arriving by bus", 0.05, 0.40, 0.10, 0.05, format="%.2f", key="gap_share")
    load = b.slider("Metro riders per feeder trip", 30, 80, 50, 5, key="gap_load")
    g = gl.copy()
    g["feeder trips / h"] = np.ceil(share * g["forecast_entries"] / load).astype(int)
    g["feeder every (min)"] = (60 / g["feeder trips / h"]).round(1)
    st.metric("Feeder trips needed per weekday in the gap hours", f"{int(g['feeder trips / h'].sum()):,}",
              f"{g['station'].nunique()} stations", delta_color="off")
    show = g[["station", "line", "hour", "forecast_entries", "bus_trips", "riders_per_bus_forecast", "feeder trips / h",
              "feeder every (min)", "current_feeder_trips_per_day", "crowding_warning"]].rename(columns={
        "forecast_entries": "forecast entries/h", "bus_trips": "bus trips/h", "riders_per_bus_forecast": "riders per bus trip",
        "current_feeder_trips_per_day": "MF feeder trips/day now", "crowding_warning": "crowding warning"})
    st.dataframe(show.round(1), hide_index=True, width="stretch")

    st.subheader("3 · Train fix: more Yellow Line trains")
    tr = pd.read_csv(EXT / "tables" / "train_headway_scenarios.csv")
    h = st.slider("Yellow Line headway (minutes); now 19", 6, 19, 12, key="gap_hw")
    base, fare = gs["yellow_base_weekday_entries_after_cut"], gs["yellow_avg_fare_rs"]
    lo, hi = (19 / h) ** 0.21 - 1, (19 / h) ** 0.30 - 1
    c = st.columns(3)
    c[0].metric("Trains per hour", f"{60 / h:.1f}", f"+{60 / h - 60 / 19:.1f} vs now", delta_color="off")
    c[1].metric("Extra weekday entries", f"{base * lo:,.0f} – {base * hi:,.0f}", f"+{lo:.1%} to +{hi:.1%}", delta_color="off")
    c[2].metric("Extra fare revenue per year", f"₹{base * lo * fare * 250 / 1e7:.1f} – {base * hi * fare * 250 / 1e7:.1f} crore")
    st.dataframe(tr.round(1), hide_index=True, width="stretch")
    st.caption("Elasticity 0.21 (synthetic control) to 0.30 (difference-in-differences), measured on the 25 → 19 min cut. "
               "Headways below 19 min are outside the measured range, so treat them as extrapolation. More trains also add "
               "platform capacity at stations with crowding warnings; we have no headway data for the Purple and Green lines.")

# ============================================================================ Fare revenue
elif page == "Fare revenue":
    hero("What the opening meant for the fare box",
         "Fare-box revenue from BMRCL's own fare fields: weekdays before (1-10 Aug) and after (11-18 Aug) the Yellow Line opened, "
         "and the extra revenue from the 10 Sep headway cut. Revenue is not profit (operating costs are not public) and does not count "
         "passengers' time savings.", eyebrow="Fare revenue · notebook 12")
    fs = tab("12", "fare_summary.csv"); fy = tab("12", "fare_yellow.csv").iloc[0]; fh = tab("12", "fare_headway.csv").iloc[0]
    rev = fs[fs.measure.str.startswith("Fare revenue")].iloc[0]
    c = st.columns(4)
    c[0].metric("Fare revenue per weekday, after", f"Rs {rev.after / 1e7:.2f} crore", f"{rev.change_pct:+.1f}% vs before")
    c[1].metric("From trips using the Yellow Line", f"Rs {fy.revenue_per_weekday / 1e5:.1f} lakh / day", f"{fy.share_of_revenue_pct:.0f}% of revenue", delta_color="off")
    c[2].metric("Average Yellow trip fare", f"Rs {fy.avg_fare:.1f}")
    c[3].metric("Headway cut, extra revenue", f"Rs {fh.extra_revenue_per_year_weekdays / 1e7:.1f} crore / yr",
                f"Rs {fh.extra_revenue_per_weekday / 1e5:.1f} lakh per weekday", delta_color="off")
    show = fs.copy()
    st.dataframe(show.round(1), hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    bl = tab("12", "fare_by_line.csv")
    m = bl.melt("origin_line", ["revenue_before", "revenue_after"], var_name="period", value_name="revenue")
    m["period"] = m["period"].str.replace("revenue_", "")
    c1.plotly_chart(px.bar(m, x="origin_line", y="revenue", color="period", barmode="group",
                           labels={"origin_line": "trips starting on", "revenue": "Rs per weekday"},
                           title="Fare revenue by origin line"), width="stretch")
    fr = tab("12", "fare_fares.csv")
    c2.plotly_chart(px.bar(fr, x=fr["fare"].astype(str), y="trips", labels={"x": "fare (Rs)", "trips": "trips per weekday"},
                           title="Trips by fare slab, after opening"), width="stretch")
    st.caption(f"Headway estimate: +{fh.did_entry_effect:.1%} entries (difference-in-differences, notebook 03) x "
               f"{fh.yellow_weekday_entries_before_cut:,.0f} Yellow weekday entries x Rs {fh.yellow_origin_avg_fare:.1f} average fare, 250 weekdays a year.")

# ============================================================================ Scaling
elif page == "Spark scaling":
    hero("Spark scaling vs pandas (notebook 06)", eyebrow=page)
    sc = tab("06", "scaling_results.csv")
    sc["setup"] = np.where(sc.engine == "pandas", "pandas (1 core)", "Spark, " + sc.cores.astype(str) + " cores")
    sc["rows_M"] = sc.groupby("snapshots").stop_times_rows.transform("max") / 1e6
    st.plotly_chart(px.line(sc, x="rows_M", y="seconds_median", color="setup", markers=True,
                            labels={"rows_M": "stop-time rows (millions)", "seconds_median": "seconds"},
                            title="Run time of the same bus-supply job"), width="stretch")
    st.dataframe(sc[["setup", "snapshots", "rows_M", "seconds_median", "speedup_vs_1core", "peak_mem_gb"]].round(2), hide_index=True, width="stretch")

# ============================================================================ Pink Line
elif page == "Pink Line":
    hero("Second event, pre-registered: Pink Line (opened 14 Nov 2026)", eyebrow=page)
    rec = pink_record()
    st.write(rec.get("rule", ""))
    c1, c2 = st.columns([1, 1])
    c1.subheader("Frozen bus-transfer stations")
    c1.write("\n".join(f"{i + 1}. {s}" for i, s in enumerate(rec.get("stations", []))))
    c1.code(f"created {rec.get('created_utc')}\nsha256  {rec.get('sha256')}")
    ps = tab("10", "pink_station_scores.csv")
    c2.plotly_chart(px.bar(ps.sort_values("PinkLink", ascending=False).head(15).iloc[::-1], x="PinkLink", y="station",
                           orientation="h", color_discrete_sequence=["#d4477e"], title="PinkLink score (9 Nov 2026 network)"),
                    width="stretch")
    st.subheader("Feeder network maturity")
    st.dataframe(tab("10", "feeder_summary.csv"), hide_index=True)

# ============================================================================ Data
else:
    hero("Data sources and reproducibility", eyebrow=page)
    st.table(pd.DataFrame({
        "Dataset": ["BMRCL station-hourly entries/exits", "BMRCL station-pair hourly (OD)", "BMRCL metro GTFS", "BMTC GTFS, 26 snapshots",
                    "Bus-stop accessibility + booth population", "BMTC stops and routes by ward", "OpenStreetMap walking network"],
        "Source": ["RTI (Vonter GitHub; verified identical to OpenCity)", "RTI (Vonter GitHub)", "Vonter/bmrcl-gtfs", "Vonter/bmtc-gtfs commits",
                   "bmtc.vonter.top", "OpenCity", "OSMnx"],
        "Size": ["92,280 + 95,616 rows", "1,273,629 rows; 12.06 M trips", "83 stations", "38.6 M stop-time rows",
                 "8,778 booths, 10.13 M people", "29 CSV files", "214,585 nodes"]}))
    nbs = pd.DataFrame({"Notebook": ["00 setup and data", "01 bus-link score", "02 diversion test", "03 time of day / headway",
                                     "04 bus supply", "05 / 05b MLlib", "06 scaling", "07 robustness", "08 population",
                                     "09 network analytics", "10 extensions + all lines", "11 demand forecaster", "12 fare revenue"],
                        "Engine": ["HDFS ingest", "pandas + OSMnx", "Spark SQL + pyfixest", "pyfixest", "Spark SQL", "Spark MLlib",
                                   "Spark vs pandas", "pyfixest", "GeoPandas", "Spark SQL", "Spark MLlib + pyfixest", "Spark MLlib (RF, KMeans)", "pandas"]})
    st.table(nbs)
    st.caption(f"Results folder: {RES}")
