"""Lunar South Pole Site Suitability Ranker - Streamlit dashboard (P3).

Run:  streamlit run app/main.py      (or `make run`)

Reads (all local, no network):
  data/processed/features.parquet  - P1, shared contract in config.yaml
  results/*                        - P2's committed outputs (predictions, pairs,
                                     validation, metrics), via app/results_io.py
  data/processed/pairs.parquet     - fallback if results/pairs.parquet is absent

Scores are computed live with P1's src/scoring.py and src/constraints.py (the one
scoring definition), so the weight sliders re-rank instantly.

If features.parquet is missing the app falls back to an in-memory SYNTHETIC
dataset so the UI can always be demoed. The banner says which mode is active.
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
import yaml

ROOT = Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / "config.yaml"
if str(ROOT) not in sys.path:          # `streamlit run app/main.py` only puts app/ on the path
    sys.path.insert(0, str(ROOT))

if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

import results_io  # noqa: E402  (reads P2's results/)
from src.constraints import landing_mask  # noqa: E402
from src.grid import build_grid, lonlat_to_xy, xy_to_lonlat  # noqa: E402  (shared 1 km grid)
from src.scoring import normalise as _normalise, weighted as _weighted  # noqa: E402

# `width="stretch"` on new Streamlit, `use_container_width=True` on older pins.
_STRETCH = ({"width": "stretch"} if "width" in inspect.signature(st.dataframe).parameters
            else {"use_container_width": True})

# Where each layer comes from (matches docs/DATA.md and the pitch deck).
SOURCES = {
    "slope_mean": "LOLA DEM (NASA PGDA)", "slope_max": "LOLA DEM (NASA PGDA)",
    "roughness": "LOLA DEM (NASA PGDA)", "crater_density": "Derived from LOLA DEM (TBD)",
    "boulder_density": "Chandrayaan-2 OHRC (not used in v1)",
    "illum_frac": "LOLA illumination maps (PDS LOLA node)",
    "psr_frac": "LOLA illumination maps (PDS LOLA node)",
    "temp_mean": "LRO Diviner PRP (PDS Geosciences)", "temp_max": "LRO Diviner PRP (PDS Geosciences)",
    "ice_cpr": "Chandrayaan-2 DFSAR (ISSDC PRADAN)",
    "hydration_depth": "Chandrayaan-2 IIRS (ISSDC PRADAN)", "earth_los_frac": "Derived from LOLA DEM",
}
VIEWS = {"Combined": "combined", "Landing": "landing", "Resource": "resource"}

# ---- look: "lunar ops console". Colours/fonts/corners live in .streamlit/config.toml;
# this adds what the theme can't: HUD brackets, scanlines, hazard stripes, mono numbers.
# ONE palette, shared with .streamlit/config.toml. From the team's reference swatches:
# Fae Fruit (coral accent), Opal (violet data), Blood Bargain (crimson alerts),
# Thorn Crown (plum panels).
PALETTE = {'bg': '#120A17', 'panel': '#1C0F24', 'panel2': '#2D1036', 'border': '#3B2048', 'text': '#EDE3EA', 'dim': '#9C8AA6', 'accent': '#D97352', 'accent_soft': '#EBA588', 'data': '#9A86DA', 'ok': '#C9A6E0', 'alert': '#C2476B'}
ORANGE, CYAN, GREEN, RED, DIM = (PALETTE["accent"], PALETTE["data"], PALETTE["ok"],
                                 PALETTE["alert"], PALETTE["dim"])
BG, PANEL, BORDER, TEXT = PALETTE["bg"], PALETTE["panel"], PALETTE["border"], PALETTE["text"]
MONO = "'Share Tech Mono', ui-monospace, monospace"
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@500;700;900&display=swap');
/* deep-space gradient on the page root; the star canvas (starfield.js) sits just above it */
html {{ background:
    radial-gradient(1100px 700px at 12% -5%, rgba(104,80,173,.48), transparent 62%),
    radial-gradient(1000px 650px at 100% 35%, rgba(46,70,170,.36), transparent 60%),
    radial-gradient(900px 600px at 30% 110%, rgba(107,7,51,.30), transparent 60%),
    linear-gradient(165deg, #140B26 0%, #0C0A1E 45%, #080C1F 100%) fixed; }}
body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stBottom"] > div,
header[data-testid="stHeader"] {{ background: transparent !important; }}
.stElementContainer:has(> iframe[height="0"]) {{ display: none; }}
/* liquid glass: frosted translucent panel, bright top edge, soft depth */
[data-testid="stDataFrame"], .stPlotlyChart, [data-testid="stMetric"], [data-testid="stExpander"] details,
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stAlert"], .ops-hero {{
  background: linear-gradient(160deg, rgba(255,255,255,.075), rgba(255,255,255,.02) 45%, rgba(154,134,218,.05)) !important;
  backdrop-filter: blur(18px) saturate(160%); -webkit-backdrop-filter: blur(18px) saturate(160%);
  border: 1px solid rgba(255,255,255,.11) !important; border-radius: 16px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.18), inset 0 -1px 0 rgba(255,255,255,.04),
              0 12px 40px rgba(4,2,12,.45);
  transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease; }}
[data-testid="stMetric"]:hover, .stPlotlyChart:hover, [data-testid="stDataFrame"]:hover {{
  border-color: rgba(235,165,136,.35) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.24), 0 16px 48px rgba(4,2,12,.55), 0 0 24px rgba(154,134,218,.12); }}
[data-testid="stMetric"]:hover {{ transform: translateY(-2px); }}
[data-testid="stDataFrame"] {{ overflow: hidden; padding: 4px; }}
/* the moon map floats in space: no box, just a soft halo behind the disc */
.st-key-moonmap .stPlotlyChart {{ background: radial-gradient(circle at 50% 52%, rgba(154,134,218,.16), rgba(104,80,173,.05) 38%, transparent 62%) !important;
  backdrop-filter: none; -webkit-backdrop-filter: none; border-color: transparent !important; box-shadow: none; }}
.st-key-moonmap .stPlotlyChart:hover {{ box-shadow: none; border-color: transparent !important; }}
.st-key-moonmap .stPlotlyChart {{ border: 0 !important; }}
.st-key-moonmap, .st-key-moonmap .stPlotlyChart, .st-key-moonmap .js-plotly-plot {{ overflow: clip !important;
  scrollbar-width: none; }}
.st-key-moonmap ::-webkit-scrollbar, .st-key-moonmap::-webkit-scrollbar {{ display: none; }}
/* gentle arrival so the page doesn't just snap in */
@keyframes luna-rise {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: none; }} }}
.ops-hero, .stPlotlyChart, [data-testid="stDataFrame"], [data-testid="stMetric"] {{ animation: luna-rise .6s ease-out both; }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}
h1, h2, h3 {{ text-transform: uppercase; letter-spacing: .12em; }}
h3 {{ font-size: 1.05rem !important; color: {ORANGE}; border-left: 3px solid {ORANGE};
      padding-left: .6rem !important; }}
/* hero header */
.ops-hero {{ padding: 16px 20px 12px; position: relative; }}
.ops-kicker {{ font-family: {MONO}; color: {ORANGE}; font-size: .78rem; letter-spacing: .25em; }}
.ops-title {{ font-family: Orbitron, sans-serif; font-weight: 900; font-size: clamp(1.4rem, 3vw, 2.3rem);
  letter-spacing: .08em; text-transform: uppercase; color: {TEXT}; line-height: 1.15; margin: 4px 0; }}
.ops-sub {{ font-family: {MONO}; color: {DIM}; font-size: .8rem; letter-spacing: .12em; }}
.ops-sub b {{ color: {GREEN}; font-weight: 400; }}
.ops-hazard {{ height: 6px; margin: 10px 0 4px;
  background: repeating-linear-gradient(-45deg, {ORANGE} 0 10px, {BG} 10px 20px); opacity: .55; }}
/* metric tiles: HUD panel with corner brackets */
[data-testid="stMetric"] {{ padding: 12px 14px; position: relative; }}
[data-testid="stMetricLabel"] p {{ font-family: {MONO}; text-transform: uppercase; letter-spacing: .14em;
  font-size: .72rem !important; color: {DIM}; }}
[data-testid="stMetricValue"] {{ font-family: {MONO}; color: {CYAN}; }}
/* controls: one label style, one option style, one value style */
[data-testid="stWidgetLabel"] p {{ font-family: {MONO}; font-size: .78rem !important; letter-spacing: .1em;
  text-transform: uppercase; color: {DIM} !important; }}
[role="radiogroup"] label p, [data-testid="stCheckbox"] label p {{ font-family: {MONO}; font-size: .85rem !important;
  letter-spacing: .04em; color: {TEXT}; text-transform: none; }}
[data-testid="stSliderThumbValue"], [data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"],
[data-testid="stNumberInput"] input {{ font-family: {MONO} !important; font-size: .85rem !important; }}
.ops-label {{ font-family: {MONO}; font-size: .78rem; letter-spacing: .22em; color: {ORANGE}; text-transform: uppercase;
  margin: 2px 0 6px; }}
.ops-legend {{ font-family: {MONO}; font-size: .8rem; color: {DIM}; letter-spacing: .04em; line-height: 1.7; }}
.ops-legend b {{ color: {TEXT}; font-weight: 400; }}
/* map toolbar: always visible, readable */
.modebar {{ opacity: 1 !important; }}
.modebar-group {{ background: rgba(28,15,36,.55) !important; backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,.12); border-radius: 10px; padding: 2px !important; }}
[data-testid="stExpander"] summary p {{ font-family: {MONO}; text-transform: uppercase; letter-spacing: .14em; }}
[data-testid="stAlert"] {{ font-family: {MONO}; letter-spacing: .03em; }}
.stCaption, [data-testid="stCaptionContainer"] {{ font-family: {MONO}; color: {DIM} !important; letter-spacing: .04em; }}
button[kind] {{ text-transform: uppercase; letter-spacing: .14em; font-family: {MONO}; }}
hr {{ border-color: {BORDER} !important; }}
</style>
"""


def style_fig(fig: go.Figure) -> go.Figure:
    """Plotly in the console look: transparent paper, mono labels, dim grid."""
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=MONO, color=DIM, size=12),
                      hoverlabel=dict(bgcolor="rgba(28,15,36,.88)", bordercolor="rgba(235,165,136,.6)",
                                      font=dict(family=MONO, color=TEXT)))
    fig.update_xaxes(gridcolor="rgba(255,255,255,.06)", zerolinecolor="rgba(255,255,255,.1)",
                     linecolor="rgba(255,255,255,.1)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,.06)", zerolinecolor="rgba(255,255,255,.1)",
                     linecolor="rgba(255,255,255,.1)")
    return fig



@st.cache_data(show_spinner=False)
def load_config() -> dict:
    return yaml.safe_load(CFG_PATH.read_text())


def _synthetic_features(cfg: dict, seed: int = 7) -> pd.DataFrame:
    """SYNTHETIC smooth fake fields on the shared 1 km polar grid (src/grid.py).
    Demo/fallback only: used when features.parquet doesn't exist yet."""
    rng = np.random.default_rng(seed)
    df = build_grid(cfg)[["cell_id", "row", "col", "x", "y", "lat", "lon"]]
    X, Y = df["x"].to_numpy(), df["y"].to_numpy()

    def field(scale: int) -> np.ndarray:
        f = np.zeros_like(X)
        for _ in range(8):
            kx, ky = rng.normal(0, 1, 2) * (2 * np.pi / (scale * 1000))
            f += np.sin(kx * X + ky * Y + rng.uniform(0, 6.28))
        return (f - f.mean()) / f.std()

    def unit(f):
        return 1 / (1 + np.exp(-f))

    slope = np.clip(6 + 4 * field(40) + rng.normal(0, 1, X.shape), 0.2, 35)
    d = {
        "slope_mean": slope,
        "slope_max": slope * 2.2,
        "roughness": np.clip(3 + 1.5 * field(30) + 0.4 * slope / 6 + rng.normal(0, .3, X.shape), 0.1, 15),
        "boulder_density": np.clip(15 + 12 * field(25), 0, 120),
        "crater_density": np.clip(20 + 10 * field(35), 0, 80),
        "illum_frac": unit(1.5 * field(60) - 1.5),
        "psr_frac": unit(2 * field(45) - 1.2),
        "temp_mean": 110 + 40 * unit(field(50)),
        "temp_max": 90 + 200 * unit(field(50) + 0.5),
        "ice_cpr": np.clip(0.6 + 0.35 * field(45) + rng.normal(0, .08, X.shape), 0, 2),
        "hydration_depth": unit(1.2 * field(55) - 2) * 0.2,
        "earth_los_frac": unit(1.3 * field(70)),
    }
    df = df.copy()
    for k, v in d.items():
        df[k] = v.astype("float32")
        df[k + "_cov"] = False  # nothing here is real
    return df


@st.cache_data(show_spinner="Loading data...")
def load_features() -> tuple[pd.DataFrame, bool]:
    cfg = load_config()
    # Local pipeline output first; results/features.parquet is the committed copy used
    # when the app is deployed without the git-ignored data/ folder.
    for p in (ROOT / cfg["paths"]["processed"] / "features.parquet", ROOT / "results" / "features.parquet"):
        if p.exists():
            return pd.read_parquet(p), False
    return _synthetic_features(cfg), True


@st.cache_data(show_spinner=False)
def load_results() -> dict:
    """P2's committed results/ (each entry None if missing; never raises)."""
    return results_io.load_results(ROOT / "results")


def load_pairs(res: dict) -> tuple[pd.DataFrame | None, str]:
    """results/pairs.parquet first, then data/processed/pairs.parquet."""
    if res["pairs"] is not None:
        return res["pairs"], "results/pairs.parquet"
    p = ROOT / load_config()["paths"]["processed"] / "pairs.parquet"
    return (pd.read_parquet(p), "data/processed/pairs.parquet") if p.exists() else (None, "")


@st.cache_data(show_spinner=False)
def load_attribution() -> pd.DataFrame | None:
    """P2's attribution table, if it ships one (feature, source, url ...)."""
    for name in ("attribution.parquet", "attribution.csv"):
        p = ROOT / load_config()["paths"]["processed"] / name
        if p.exists():
            return pd.read_parquet(p) if name.endswith(".parquet") else pd.read_csv(p)
    return None


def _demo_pairs(feats: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """SYNTHETIC placeholder pairs so the table renders before P2's pairs.parquet exists.
    Random landing cells and random distances: NOT computed, never present as results."""
    rng = np.random.default_rng(1)
    land = feats.sample(40, random_state=2)
    return pd.DataFrame({
        "landing_cell_id": land["cell_id"].astype(int).to_numpy(),
        "distance_km": rng.uniform(1, cfg["pairing"]["radius_km"], len(land)).round(2),
        "data": "SYNTHETIC placeholder",
    })



@st.cache_data(show_spinner=False)
def normalised(feats: pd.DataFrame) -> pd.DataFrame:
    """0-1 goodness per feature from src/scoring.py. Weight-independent, so cached."""
    return _normalise(feats, load_config())


def weighted_score(norm: pd.DataFrame, weights: dict[str, float],
                   feats: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(score 0-100, confidence 0-1) from src/scoring.py: weights renormalised over the
    features a cell has; confidence = share of weight backed by real data."""
    score, conf = _weighted(norm, weights, feats)
    return 100 * score, conf


def pick_top(df: pd.DataFrame, col: str, n: int, min_sep_m: float) -> pd.DataFrame:
    """Top-N cells with a minimum spacing so the list isn't 10 neighbours."""
    cand = df.dropna(subset=[col]).nlargest(3000, col)
    xs, ys, keep = cand.x.to_numpy(), cand.y.to_numpy(), []
    for i in range(len(cand)):
        if all(np.hypot(xs[i] - xs[j], ys[i] - ys[j]) >= min_sep_m for j in keep):
            keep.append(i)
            if len(keep) == n:
                break
    return cand.iloc[keep]



GRATICULE_LATS = (-80, -82, -84, -86, -88)
MAP_TOOLS = {"displaylogo": False, "displayModeBar": True,
             "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines",
                                        "hoverClosestCartesian", "hoverCompareCartesian"],
             "toImageButtonOptions": {"format": "png", "filename": "lunar_south_pole_map", "scale": 2}}


def _lon_label(lon: float) -> str:
    lon = (lon + 180) % 360 - 180
    return "0°" if lon == 0 else "180°" if abs(lon) == 180 else f"{abs(lon):.0f}°{'E' if lon > 0 else 'W'}"


def heatmap(df: pd.DataFrame, col: str, cell_m: float, top: pd.DataFrame, sel_id, label: str,
            val_pts: pd.DataFrame | None = None, bin_km: float = 2.0) -> go.Figure:
    """Polar stereographic score map with a lat/lon graticule (same projection as LOLA)."""
    f = max(1, round(bin_km * 1000 / cell_m))
    r = ((df.y - df.y.min()) // cell_m).astype(int) // f
    c = ((df.x - df.x.min()) // cell_m).astype(int) // f
    g = pd.DataFrame({"r": r, "c": c, "x": df.x, "y": df.y, "v": df[col], "l": df.landing,
                      "s": df.resource, "k": df.combined}).groupby(["r", "c"]).mean().reset_index()
    xs = g.groupby("c").x.mean().sort_index(); ys = g.groupby("r").y.mean().sort_index()
    ri, ci = ys.index.get_indexer(g.r), xs.index.get_indexer(g.c)
    shape = (len(ys), len(xs))
    grids = {k: np.full(shape, np.nan) for k in ("v", "l", "s", "k")}
    for k in grids:
        grids[k][ri, ci] = g[k]
    gx, gy = np.meshgrid(xs.values, ys.values)
    lon, lat = xy_to_lonlat(gx, gy)
    custom = np.dstack([lat, lon, grids["l"], grids["s"], grids["k"]])
    fig = go.Figure(go.Heatmap(
        z=grids["v"], x=xs.values / 1000, y=ys.values / 1000, colorscale="Viridis", zmin=0, zmax=100,
        customdata=custom, name="score", opacity=0.93,
        colorbar=dict(title=dict(text=f"{label.upper()}<br>0–100", side="top"), outlinewidth=0,
                      thickness=14, len=0.68, y=0.4, yanchor="middle"),
        hovertemplate=("<b>lat %{customdata[0]:.2f}°, lon %{customdata[1]:.1f}°</b><br>"
                       "landing %{customdata[2]:.0f} · resource %{customdata[3]:.0f} · combined %{customdata[4]:.0f}"
                       "<br>x %{x:.0f} km, y %{y:.0f} km<extra></extra>")))
    # graticule: latitude rings every 2°, longitude spokes every 30°
    ring = np.radians(np.linspace(0, 360, 241))
    for la in GRATICULE_LATS:
        rx, _ = lonlat_to_xy(90.0, la)                     # radius of this latitude ring (m)
        rad = abs(rx) / 1000
        fig.add_trace(go.Scatter(x=rad * np.sin(ring), y=rad * np.cos(ring), mode="lines", hoverinfo="skip",
                                 line=dict(color="rgba(237,227,234,.28)", width=1, dash="dot"), showlegend=False))
        lx, ly = lonlat_to_xy(135.0, la)
        fig.add_annotation(x=lx / 1000, y=ly / 1000, text=f"{abs(la)}°S", showarrow=False,
                           font=dict(family=MONO, size=11, color=TEXT), bgcolor="rgba(18,10,23,.65)")
    r80 = abs(lonlat_to_xy(90.0, -80)[0]) / 1000
    for w, a in ((22, .05), (12, .09), (5, .16), (1.5, .45)):   # soft glow around the 80°S edge
        fig.add_trace(go.Scatter(x=r80 * 1.01 * np.sin(ring), y=r80 * 1.01 * np.cos(ring), mode="lines",
                                 hoverinfo="skip", showlegend=False,
                                 line=dict(color=f"rgba(190,175,255,{a})", width=w)))
    for lo in range(0, 360, 30):
        a = np.radians(lo)
        fig.add_trace(go.Scatter(x=[0, r80 * np.sin(a)], y=[0, r80 * np.cos(a)], mode="lines", hoverinfo="skip",
                                 line=dict(color="rgba(237,227,234,.18)", width=1, dash="dot"), showlegend=False))
        fig.add_annotation(x=1.07 * r80 * np.sin(a), y=1.07 * r80 * np.cos(a), text=_lon_label(lo),
                           showarrow=False, font=dict(family=MONO, size=11, color=DIM))
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", text=["S POLE"], textposition="top center",
                             textfont=dict(family=MONO, size=11, color=TEXT), hoverinfo="skip", showlegend=False,
                             marker=dict(symbol="cross-thin", size=14, line=dict(color=TEXT, width=2))))
    if len(top):
        fig.add_trace(go.Scatter(
            x=top.x / 1000, y=top.y / 1000, mode="markers+text", text=[str(i + 1) for i in range(len(top))],
            textposition="top center", textfont=dict(color=TEXT, size=12, family=MONO), name="Top-N sites",
            marker=dict(size=10, symbol="square", color=BG, line=dict(color=TEXT, width=2)),
            customdata=np.c_[top.cell_id, top.lat, top.lon],
            hovertemplate="<b>#%{text}</b> cell %{customdata[0]}<br>%{customdata[1]:.2f}°, %{customdata[2]:.1f}°E<extra></extra>"))
    if val_pts is not None and len(val_pts):
        fig.add_trace(go.Scatter(
            x=val_pts.x / 1000, y=val_pts.y / 1000, mode="markers+text", text=val_pts.name,
            textposition="bottom center", textfont=dict(color=GREEN, size=11, family=MONO), name="NASA reference",
            marker=dict(size=13, symbol="diamond", color=GREEN, line=dict(color=BG, width=2)),
            hovertext=val_pts.hover, hovertemplate="%{hovertext}<extra>NASA reference site</extra>"))
    if sel_id is not None and (df.cell_id == sel_id).any():
        s = df[df.cell_id == sel_id].iloc[0]
        fig.add_trace(go.Scatter(x=[s.x / 1000], y=[s.y / 1000], mode="markers", name="Selected site",
                                 hoverinfo="skip",
                                 marker=dict(size=24, symbol="square-open", color=TEXT, line=dict(color=TEXT, width=3))))
    lim = 1.12 * r80
    fig.update_layout(
        height=940, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", x=0, y=1.04, bgcolor="rgba(0,0,0,0)", font=dict(family=MONO, size=12)),
        modebar=dict(bgcolor=PANEL, color=TEXT, activecolor=ORANGE, orientation="v"),
        xaxis=dict(range=[-lim, lim], visible=False),
        yaxis=dict(range=[-lim, lim], visible=False, scaleanchor="x", scaleratio=1))
    return style_fig(fig)


def confidence_label(p: float) -> str:
    return "High" if p >= .75 else "Medium" if p >= .4 else "Low"


# --------------------------------------------------------------------------- app
STARFIELD_JS = (Path(__file__).parent / "starfield.js").read_text(encoding="utf-8")


def starfield() -> None:
    """Run starfield.js in the parent page (a zero-height component; Streamlit's component
    iframe is same-origin). The script tag lives in the page itself, so it survives reruns."""
    components.html(
        "<script>const d = window.parent.document;"
        "if (!d.getElementById('luna-stars-js')) {"
        " const s = d.createElement('script'); s.id = 'luna-stars-js';"
        f" s.textContent = {json.dumps(STARFIELD_JS)}; d.head.appendChild(s); }}</script>", height=0)


def main() -> None:
    st.set_page_config(page_title="Lunar South Pole Site Ranker", layout="wide", page_icon="🌘",
                       initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)
    starfield()
    cfg = load_config()
    feats, is_synth = load_features()
    cell_m = cfg["grid"]["cell_size_m"]

    st.markdown(
        f"""<div class="ops-hero">
        <div class="ops-kicker">SYS//LUNAR-OPS · SECTOR 80°S–90°S · GRID 1 KM</div>
        <div class="ops-title">Lunar South Pole Site Suitability Ranker</div>
        <div class="ops-sub">CELLS <b>{len(feats):,}</b> · FEATURES <b>{len(cfg['features'])}</b> ·
        STATUS <b>{'SYNTHETIC' if is_synth else 'LIVE DATA'}</b></div>
        <div class="ops-hazard"></div></div>""", unsafe_allow_html=True)
    cov_cols = [c for c in feats.columns if c.endswith("_cov")]
    real_pct = 100 * float(feats[cov_cols].to_numpy().mean()) if cov_cols else 0.0
    if is_synth or real_pct == 0:
        st.error("SYNTHETIC DATA - no real LOLA / Diviner / Chandrayaan-2 data is loaded. "
                 "Rankings are illustrative only and must not be read as real site recommendations.")
    elif real_pct < 100:
        st.warning(f"PARTLY SYNTHETIC - {real_pct:.0f}% of feature values are real; the rest are synthetic placeholders. "
                   "Per-site confidence shows how much of each score rests on real data.")
    res = load_results()
    if res["version"] is None:
        st.info("Model results (results/) not found yet: scores below are the live weighted rule only.")
    elif results_io.version_is_synthetic(res["version"]):
        st.warning(f"Model results in results/ were trained on SYNTHETIC features ({res['version']}).")
    for w in res["warnings"]:
        st.warning(w)
    st.caption("Decision support, not a final site selector. 80S-90S on a 1 km grid.")

    # ---- control bar (horizontal, one row) + feature weights below it
    with st.container(border=True):
        st.markdown('<div class="ops-label">Controls</div>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns([2.4, 2.2, 1.2, 1.9, 1.3], gap="medium", vertical_alignment="bottom")
        view_name = c1.radio("Map shows", list(VIEWS), horizontal=True, key="view")
        view = VIEWS[view_name]
        mix = c2.slider("Combined: resource share", 0.0, 1.0, 0.5, 0.05, key="mix",
                        help="0 = landing only, 1 = resource only")
        top_n = int(c3.number_input("Top-N sites", 3, 50, cfg["pairing"]["top_n"], key="top_n"))
        hide = c4.checkbox("Hide unsafe landing cells", True, key="hide",
                           help="Cells failing a hard landing rule (slope, roughness, boulders)")
        if c5.button("Reset weights", **_STRETCH):
            for k in [k for k in st.session_state if k.startswith("w_")]:
                del st.session_state[k]
        weights: dict[str, dict[str, float]] = {}
        with st.expander("Feature weights · landing and resource", expanded=False):
            cols = st.columns(2, gap="large")
            for col, (grp, title) in zip(cols, (("landing", "Landing"), ("resource", "Resource"))):
                col.markdown(f'<div class="ops-label">{title} weights</div>', unsafe_allow_html=True)
                weights[grp] = {}
                for f, spec in cfg["scoring"][grp].items():
                    weights[grp][f] = col.slider(f"{f} · {spec['direction']} is better", 0.0, 1.0,
                                                 float(spec["weight"]), 0.05, key=f"w_{grp}_{f}")

    # ---- live scoring (vectorised; instant)
    norm = normalised(feats)
    df = feats[["cell_id", "x", "y", "lat", "lon"]].copy()
    df["landing"], df["landing_conf"] = weighted_score(norm, weights["landing"], feats)
    df["resource"], df["resource_conf"] = weighted_score(norm, weights["resource"], feats)
    df["eligible"] = landing_mask(feats, cfg).to_numpy()
    if hide:
        df.loc[~df.eligible, "landing"] = np.nan
    df["combined"] = (1 - mix) * df.landing + mix * df.resource  # NaN if either is NaN
    top = pick_top(df, view, top_n, min_sep_m=5000)
    sel_key = "selected_cell"

    # ---- map, full width
    st.subheader(f"South polar map · {view_name}")
    # Read the picker's own key: it already holds this run's choice, so the box
    # never lags one click behind (sel_key is only set further down the script).
    val_pts = results_io.validation_points(res["validation"], feats, cfg["moon"]["radius_m"],
                                           cfg["grid"]["lat_limit_deg"])
    st.plotly_chart(heatmap(df, view, cell_m, top, st.session_state.get("site_pick"), view_name, val_pts),
                    config=MAP_TOOLS, key="moonmap", **_STRETCH)
    st.markdown(
        f"""<div class="ops-legend">
        <b>How to read it:</b> polar stereographic view of 80°S–90°S, the same projection as NASA’s LOLA maps;
        the pole is at the centre, dotted rings mark latitude every 2°, spokes mark longitude every 30°.
        Each pixel is the mean {view_name.lower()} score of a 2 km block (0 = poor, 100 = best).
        {"Gaps where space shows through are cells that fail a hard landing rule (steep crater walls)." if hide else ""}<br>
        <b>Map tools (top right):</b> zoom box · pan · zoom in / out · reset view (house) · save as PNG.
        Scroll to zoom, double-click to reset. Hover any pixel for its latitude, longitude and all three scores.
        </div>""", unsafe_allow_html=True)

    st.divider()
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.subheader(f"Top {len(top)} · {view_name}")
        tl = top[["cell_id", "lat", "lon", "landing", "resource", "combined"]].round(2).reset_index(drop=True)
        tl.index = tl.index + 1
        st.dataframe(tl, **_STRETCH, height=35 * (len(tl) + 1) + 3)

    with right:
        st.subheader("Site detail")
        if top.empty:
            st.info("No cells to show - relax the constraints or weights.")
        else:
            ids = top.cell_id.tolist()
            labels = {cid: f"#{i + 1}  cell {cid}" for i, cid in enumerate(ids)}
            cid = st.selectbox("Site", ids, format_func=labels.get, key="site_pick")
            st.session_state[sel_key] = cid
            site_card(feats, df, norm, cid, weights, cfg, res)

    st.divider()
    st.subheader("Landing / ice pairs")
    pairs_table(df, top, cfg, feats, res)
    model_panel(res)


def site_card(feats, df, norm, cid, weights, cfg, res) -> None:
    i = feats.index[feats.cell_id == cid][0]
    row, srow = feats.loc[i], df.loc[i]
    m = st.columns(3)
    m[0].metric("Landing", "-" if pd.isna(srow.landing) else f"{srow.landing:.0f}")
    m[1].metric("Resource", "-" if pd.isna(srow.resource) else f"{srow.resource:.0f}")
    m[2].metric("Combined", "-" if pd.isna(srow.combined) else f"{srow.combined:.0f}")
    p = float((srow.landing_conf + srow.resource_conf) / 2)
    lab = confidence_label(p)
    pred = res["predictions"]
    if pred is not None:
        hit = pred[pred.cell_id == cid]
        if len(hit):
            h = hit.iloc[0]
            def _pm(score, unc):
                return "-" if pd.isna(score) else f"{100 * score:.0f} ± {100 * (0 if pd.isna(unc) else unc):.0f}"
            mm = st.columns(2)
            mm[0].metric("Model landing (MLP)", _pm(h.get("landing_score"), h.get("landing_uncertainty")))
            mm[1].metric("Model resource (MLP)", _pm(h.get("resource_score"), h.get("resource_uncertainty")))
            st.caption("Model = P2's MLP ensemble trained to imitate the weighted rule; ± is ensemble spread "
                       f"(uncalibrated). Features version: {res['version'] or 'unknown'}.")
    st.markdown(f"**Confidence: {lab}** - {p * 100:.0f}% of the weighting rests on real (non-synthetic) data. "
                f"Lat {row.lat:.2f}, Lon {row.lon:.1f}. "
                + ("Passes hard landing constraints." if srow.eligible else "**Fails a hard landing constraint.**"))

    attr = load_attribution()
    rows = []
    for grp in ("landing", "resource"):
        tw = sum(weights[grp].values()) or 1
        for f, w in weights[grp].items():
            nv = norm.at[i, f] if f in norm else np.nan
            src = SOURCES.get(f, "")
            if attr is not None and {"feature", "source"} <= set(attr.columns) and (attr.feature == f).any():
                src = str(attr.loc[attr.feature == f, "source"].iloc[0])
            rows.append({"group": grp, "feature": f, "value": row.get(f, np.nan),
                         "unit": cfg["features"][f]["unit"], "goodness (0-1)": nv,
                         "contribution": 0 if pd.isna(nv) else 100 * nv * w / tw,
                         "real data": bool(row.get(f + "_cov", False)), "source": src})
    t = pd.DataFrame(rows)
    fig = go.Figure(go.Bar(x=t.contribution, y=t.feature, orientation="h",
                           marker_color=[CYAN if g == "landing" else ORANGE for g in t.group],
                           hovertemplate="%{y}: %{x:.1f} pts<extra></extra>"))
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0), xaxis_title="SCORE POINTS",
                      yaxis=dict(autorange="reversed"))
    st.plotly_chart(style_fig(fig), **_STRETCH)
    st.caption("Points each feature adds to its group score. Violet = landing, coral = resource.")
    show = t.drop(columns=["contribution", "group"]).round(3)
    show["real data"] = show["real data"].map({True: "real", False: "SYNTHETIC / none"})
    st.dataframe(show, **_STRETCH, hide_index=True)


def pairs_table(df, top, cfg, feats, res) -> None:
    pairs, src = load_pairs(res)
    if pairs is None:
        st.warning("SYNTHETIC placeholder pairs: pairs.parquet (P2) not found yet. "
                   "These landing cells and distances are random, not computed.")
        pairs = _demo_pairs(feats, cfg)
    lid = next((c for c in pairs.columns if "land" in c.lower() and "id" in c.lower()), None)
    dcol = next((c for c in pairs.columns if "dist" in c.lower()), None)
    only_top = False
    if lid:
        only_top = st.checkbox("Only pairs whose landing cell is in the current top-N", False)
        if only_top:
            pairs = pairs[pairs[lid].isin(top.cell_id)]
        pairs = pairs.merge(df[["cell_id", "landing"]].rename(columns={"cell_id": lid, "landing": "landing_score_live"}),
                            on=lid, how="left")
    if "combined_score" in pairs:
        pairs = pairs.sort_values("combined_score", ascending=False)
    elif dcol:
        pairs = pairs.sort_values(dcol)
    st.dataframe(pairs.round(3), **_STRETCH, hide_index=True, height=320)
    st.caption(f"{len(pairs):,} pairs, pairing radius {cfg['pairing']['radius_km']} km. "
               f"Source: {src or 'SYNTHETIC placeholder'}. landing_score_live (0-100) updates with the sliders; "
               "route_cost = distance x mean slope, a heuristic, not a path plan.")


def model_panel(res) -> None:
    """P2's metrics.json: MLP vs Ridge baseline on held-out spatial blocks."""
    m = res["metrics"]
    with st.expander("About the model", expanded=False):
        if not isinstance(m, dict):
            st.write("results/metrics.json not found yet (P2 commits it after training).")
            return
        items = results_io.r2_items(m, limit=8)
        if items:
            cols = st.columns(min(4, len(items)))
            for i, (k, v) in enumerate(items):
                label = k.removeprefix("metrics.").replace("_score/", " ").replace("_with_masked_inputs", " (masked)")
                cols[i % len(cols)].metric(f"R² {label}", f"{v:.3f}")
        st.caption("R² = how well the model reproduces the weighted scoring rule on held-out 10 km blocks. "
                   "It is not landing accuracy: there are no ground-truth labels for 'good' sites. "
                   f"Features version: {res['version'] or 'unknown'}.")
        st.dataframe(results_io.flatten_metrics(m), **_STRETCH, hide_index=True)


if __name__ == "__main__":
    main()
