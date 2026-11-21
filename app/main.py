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
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / "config.yaml"
if str(ROOT) not in sys.path:          # `streamlit run app/main.py` only puts app/ on the path
    sys.path.insert(0, str(ROOT))

if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

import results_io  # noqa: E402  (reads P2's results/)
from src.constraints import landing_mask  # noqa: E402
from src.grid import build_grid  # noqa: E402  (shared 1 km grid, same cell_ids as the pipeline)
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
VIEWS = {"Combined": "combined", "Landing safety": "landing", "Resource value": "resource"}

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
.stApp {{
  background:
    radial-gradient(1200px 600px at 85% -10%, rgba(217,115,82,.06), transparent 60%),
    radial-gradient(900px 500px at -10% 110%, rgba(104,80,173,.10), transparent 60%),
    {BG};
}}
/* faint scanlines over everything, never blocking clicks */
.stApp::after {{
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 999;
  background: repeating-linear-gradient(0deg, rgba(255,255,255,.010) 0 1px, transparent 1px 3px);
}}
header[data-testid="stHeader"] {{ background: transparent; }}
h1, h2, h3 {{ text-transform: uppercase; letter-spacing: .12em; }}
h3 {{ font-size: 1.05rem !important; color: {ORANGE}; border-left: 3px solid {ORANGE};
      padding-left: .6rem !important; }}
/* hero header */
.ops-hero {{ border: 1px solid {BORDER}; border-left: 4px solid {ORANGE}; padding: 14px 18px 12px;
  background: linear-gradient(90deg, rgba(217,115,82,.10), rgba(45,16,54,.55) 40%); position: relative; }}
.ops-kicker {{ font-family: {MONO}; color: {ORANGE}; font-size: .78rem; letter-spacing: .25em; }}
.ops-title {{ font-family: Orbitron, sans-serif; font-weight: 900; font-size: clamp(1.4rem, 3vw, 2.3rem);
  letter-spacing: .08em; text-transform: uppercase; color: {TEXT}; line-height: 1.15; margin: 4px 0; }}
.ops-sub {{ font-family: {MONO}; color: {DIM}; font-size: .8rem; letter-spacing: .12em; }}
.ops-sub b {{ color: {GREEN}; font-weight: 400; }}
.ops-hazard {{ height: 6px; margin: 10px 0 4px;
  background: repeating-linear-gradient(-45deg, {ORANGE} 0 10px, {BG} 10px 20px); opacity: .55; }}
/* metric tiles: HUD panel with corner brackets */
[data-testid="stMetric"] {{ background: {PANEL}; border: 1px solid {BORDER}; padding: 10px 12px; position: relative; }}
[data-testid="stMetric"]::before, [data-testid="stMetric"]::after {{ content: ""; position: absolute;
  width: 10px; height: 10px; border-color: {ORANGE}; border-style: solid; }}
[data-testid="stMetric"]::before {{ top: -1px; left: -1px; border-width: 2px 0 0 2px; }}
[data-testid="stMetric"]::after {{ bottom: -1px; right: -1px; border-width: 0 2px 2px 0; }}
[data-testid="stMetricLabel"] p {{ font-family: {MONO}; text-transform: uppercase; letter-spacing: .14em;
  font-size: .72rem !important; color: {DIM}; }}
[data-testid="stMetricValue"] {{ font-family: {MONO}; color: {CYAN}; }}
/* sidebar = control rack */
section[data-testid="stSidebar"] h2 {{ font-size: .95rem; color: {ORANGE}; }}
section[data-testid="stSidebar"] label p {{ font-family: {MONO}; font-size: .78rem; letter-spacing: .06em; }}
/* panels, tables, alerts: hard edges and a lit top rule */
[data-testid="stExpander"] details, [data-testid="stDataFrame"], .stPlotlyChart {{
  border: 1px solid {BORDER}; box-shadow: inset 0 1px 0 rgba(217,115,82,.28); }}
[data-testid="stExpander"] summary p {{ font-family: {MONO}; text-transform: uppercase; letter-spacing: .14em; }}
[data-testid="stAlert"] {{ font-family: {MONO}; letter-spacing: .03em; border-left: 4px solid currentColor; }}
.stCaption, [data-testid="stCaptionContainer"] {{ font-family: {MONO}; color: {DIM} !important; letter-spacing: .04em; }}
button[kind] {{ text-transform: uppercase; letter-spacing: .14em; font-family: {MONO}; }}
hr {{ border-color: {BORDER} !important; }}
</style>
"""


def style_fig(fig: go.Figure) -> go.Figure:
    """Plotly in the console look: transparent paper, mono labels, dim grid."""
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=BG,
                      font=dict(family=MONO, color=DIM, size=12),
                      hoverlabel=dict(bgcolor=PANEL, bordercolor=ORANGE, font=dict(family=MONO, color=TEXT)))
    fig.update_xaxes(gridcolor="#24132C", zerolinecolor=BORDER, linecolor=BORDER)
    fig.update_yaxes(gridcolor="#24132C", zerolinecolor=BORDER, linecolor=BORDER)
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



def heatmap(df: pd.DataFrame, col: str, cell_m: float, top: pd.DataFrame, sel_id, label: str,
            val_pts: pd.DataFrame | None = None) -> go.Figure:
    f = max(1, round(5000 / cell_m))  # ~5 km bins for speed
    r = ((df.y - df.y.min()) // cell_m).astype(int) // f
    c = ((df.x - df.x.min()) // cell_m).astype(int) // f
    g = pd.DataFrame({"r": r, "c": c, "x": df.x, "y": df.y, "v": df[col]}).groupby(["r", "c"]).agg(
        x=("x", "mean"), y=("y", "mean"), v=("v", "mean")).reset_index()
    xs = g.groupby("c").x.mean().sort_index(); ys = g.groupby("r").y.mean().sort_index()
    z = np.full((len(ys), len(xs)), np.nan)
    z[ys.index.get_indexer(g.r), xs.index.get_indexer(g.c)] = g.v
    fig = go.Figure(go.Heatmap(z=z, x=xs.values / 1000, y=ys.values / 1000, colorscale="Viridis",
                               zmin=0, zmax=100, colorbar=dict(title=label.upper(), outlinewidth=0, thickness=12),
                               hovertemplate="x %{x:.0f} km, y %{y:.0f} km<br>score %{z:.1f}<extra></extra>"))
    if len(top):
        fig.add_trace(go.Scatter(
            x=top.x / 1000, y=top.y / 1000, mode="markers+text", text=[str(i + 1) for i in range(len(top))],
            textposition="top center", textfont=dict(color=TEXT, size=12, family=MONO),
            marker=dict(size=10, symbol="square", color=BG, line=dict(color=TEXT, width=2)),
            customdata=top.cell_id, hovertemplate="#%{text}  cell %{customdata}<extra></extra>", showlegend=False))
    if val_pts is not None and len(val_pts):
        fig.add_trace(go.Scatter(
            x=val_pts.x / 1000, y=val_pts.y / 1000, mode="markers+text", text=val_pts.name,
            textposition="bottom center", textfont=dict(color=GREEN, size=11, family=MONO),
            marker=dict(size=13, symbol="diamond", color=GREEN, line=dict(color=BG, width=2)),
            hovertext=val_pts.hover, hovertemplate="%{hovertext}<extra>NASA reference site</extra>",
            showlegend=False))
    if sel_id is not None and (df.cell_id == sel_id).any():
        s = df[df.cell_id == sel_id].iloc[0]
        fig.add_trace(go.Scatter(x=[s.x / 1000], y=[s.y / 1000], mode="markers", showlegend=False,
                                 marker=dict(size=24, symbol="square-open", color=TEXT, line=dict(color=TEXT, width=3))))
    fig.update_layout(height=640, margin=dict(l=0, r=0, t=10, b=0), yaxis=dict(scaleanchor="x", title="km (S-polar stereographic)"),
                      xaxis=dict(title="km"))
    return style_fig(fig)


def confidence_label(p: float) -> str:
    return "High" if p >= .75 else "Medium" if p >= .4 else "Low"


# --------------------------------------------------------------------------- app
def main() -> None:
    st.set_page_config(page_title="Lunar South Pole Site Ranker", layout="wide", page_icon="🌘")
    st.markdown(CSS, unsafe_allow_html=True)
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

    # ---- sidebar: controls
    sb = st.sidebar
    sb.header("Controls")
    view_name = sb.radio("Map shows", list(VIEWS), horizontal=False)
    view = VIEWS[view_name]
    mix = sb.slider("Combined: resource weight", 0.0, 1.0, 0.5, 0.05, help="0 = landing only, 1 = resource only")
    hide = sb.checkbox("Hide cells failing hard landing constraints", True)
    top_n = int(sb.number_input("Top-N sites", 3, 50, cfg["pairing"]["top_n"]))
    if sb.button("Reset weights"):
        for k in [k for k in st.session_state if k.startswith("w_")]:
            del st.session_state[k]
    weights: dict[str, dict[str, float]] = {}
    for grp, title in (("landing", "Landing weights"), ("resource", "Resource weights")):
        with sb.expander(title, expanded=False):
            weights[grp] = {}
            for f, spec in cfg["scoring"][grp].items():
                weights[grp][f] = st.slider(f"{f} ({spec['direction']} is better)", 0.0, 1.0, float(spec["weight"]),
                                            0.05, key=f"w_{grp}_{f}")

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

    left, right = st.columns([3, 2], gap="large")
    with left:
        # Read the picker's own key: it already holds this run's choice, so the ring
        # never lags one click behind (sel_key is only set further down the script).
        val_pts = results_io.validation_points(res["validation"], feats, cfg["moon"]["radius_m"],
                                               cfg["grid"]["lat_limit_deg"])
        st.plotly_chart(heatmap(df, view, cell_m, top, st.session_state.get("site_pick"), view_name, val_pts),
                        **_STRETCH)
        st.caption("Dark squares = top-N sites (min 5 km apart). Lilac diamonds = NASA reference sites "
                   "(rank from results/validation.csv). White box = selected site. Map binned to ~5 km.")

    with right:
        st.subheader(f"Top {len(top)} - {view_name}")
        tl = top[["cell_id", "lat", "lon", "landing", "resource", "combined"]].round(2).reset_index(drop=True)
        tl.index = tl.index + 1
        st.dataframe(tl, **_STRETCH, height=300)

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
