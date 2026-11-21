"""Lunar South Pole Site Suitability Ranker - Streamlit dashboard (P3).

Run:  streamlit run app/main.py      (or `make run`)

Reads (all local, no network):
  data/processed/features.parquet  - shared contract in config.yaml
  data/processed/scores.parquet    - P1 (optional; used only to cross-check)
  data/processed/pairs.parquet     - P2 (landing cell <-> nearby ice cell)

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

from src.grid import build_grid  # noqa: E402  (shared 1 km grid, same cell_ids as the pipeline)

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
    p = ROOT / cfg["paths"]["processed"] / "features.parquet"
    if p.exists():
        return pd.read_parquet(p), False
    return _synthetic_features(cfg), True


@st.cache_data(show_spinner=False)
def load_pairs() -> pd.DataFrame | None:
    p = ROOT / load_config()["paths"]["processed"] / "pairs.parquet"
    return pd.read_parquet(p) if p.exists() else None


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
    """0-1 per feature (2nd-98th percentile clip), flipped so 1 is always 'better'.
    Independent of the weights, so it is cached and sliders stay instant."""
    cfg = load_config()["scoring"]
    out = {}
    for grp in cfg.values():
        for f, spec in grp.items():
            if f not in feats:
                continue
            v = feats[f].to_numpy("float64")
            if np.isfinite(v).sum() == 0:
                out[f] = np.full(len(v), np.nan); continue
            lo, hi = np.nanpercentile(v, [2, 98])
            n = np.clip((v - lo) / (hi - lo), 0, 1) if hi > lo else np.full(len(v), .5)
            out[f] = 1 - n if spec["direction"] == "lower" else n
    return pd.DataFrame(out, index=feats.index)


def weighted_score(norm: pd.DataFrame, weights: dict[str, float]) -> np.ndarray:
    """Weights renormalised over the features a cell actually has (config.yaml rule).
    >>> SWAP POINT: to use P1's scoring.py instead, replace the body of this
    function with a call to it - the rest of the app only needs a 0-100 array.
    """
    num = np.zeros(len(norm)); den = np.zeros(len(norm))
    for f, w in weights.items():
        if f not in norm or w <= 0:
            continue
        v = norm[f].to_numpy(); ok = ~np.isnan(v)
        num += np.where(ok, v, 0) * w; den += np.where(ok, w, 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, 100 * num / den, np.nan)


def passes_constraints(feats: pd.DataFrame, cons: dict) -> np.ndarray:
    ok = np.ones(len(feats), bool)
    for col, lim in (("slope_mean", cons["slope_mean_max_deg"]), ("roughness", cons["roughness_max_deg"]),
                     ("boulder_density", cons["boulder_density_max"])):
        if col in feats:
            ok &= ~(feats[col].to_numpy("float64") > lim)  # NaN never removes a cell
    return ok


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



def heatmap(df: pd.DataFrame, col: str, cell_m: float, top: pd.DataFrame, sel_id, label: str) -> go.Figure:
    f = max(1, round(5000 / cell_m))  # ~5 km bins for speed
    r = ((df.y - df.y.min()) // cell_m).astype(int) // f
    c = ((df.x - df.x.min()) // cell_m).astype(int) // f
    g = pd.DataFrame({"r": r, "c": c, "x": df.x, "y": df.y, "v": df[col]}).groupby(["r", "c"]).agg(
        x=("x", "mean"), y=("y", "mean"), v=("v", "mean")).reset_index()
    xs = g.groupby("c").x.mean().sort_index(); ys = g.groupby("r").y.mean().sort_index()
    z = np.full((len(ys), len(xs)), np.nan)
    z[ys.index.get_indexer(g.r), xs.index.get_indexer(g.c)] = g.v
    fig = go.Figure(go.Heatmap(z=z, x=xs.values / 1000, y=ys.values / 1000, colorscale="Viridis",
                               zmin=0, zmax=100, colorbar=dict(title=label),
                               hovertemplate="x %{x:.0f} km, y %{y:.0f} km<br>score %{z:.1f}<extra></extra>"))
    if len(top):
        fig.add_trace(go.Scatter(
            x=top.x / 1000, y=top.y / 1000, mode="markers+text", text=[str(i + 1) for i in range(len(top))],
            textposition="top center", textfont=dict(color="white", size=11),
            marker=dict(size=9, color="red", line=dict(color="white", width=1.5)),
            customdata=top.cell_id, hovertemplate="#%{text}  cell %{customdata}<extra></extra>", showlegend=False))
    if sel_id is not None and (df.cell_id == sel_id).any():
        s = df[df.cell_id == sel_id].iloc[0]
        fig.add_trace(go.Scatter(x=[s.x / 1000], y=[s.y / 1000], mode="markers", showlegend=False,
                                 marker=dict(size=18, color="rgba(0,0,0,0)", line=dict(color="cyan", width=3))))
    fig.update_layout(height=640, margin=dict(l=0, r=0, t=10, b=0), yaxis=dict(scaleanchor="x", title="km (S-polar stereographic)"),
                      xaxis=dict(title="km"))
    return fig


def confidence(feats_row: pd.Series, weights: dict[str, float]) -> tuple[float, str]:
    tot = sum(weights.values()) or 1
    real = sum(w for f, w in weights.items() if bool(feats_row.get(f + "_cov", False)) and pd.notna(feats_row.get(f)))
    p = real / tot
    return p, ("High" if p >= .75 else "Medium" if p >= .4 else "Low")


# --------------------------------------------------------------------------- app
def main() -> None:
    st.set_page_config(page_title="Lunar South Pole Site Ranker", layout="wide")
    cfg = load_config()
    feats, is_synth = load_features()
    cell_m = cfg["grid"]["cell_size_m"]

    st.title("Lunar South Pole Site Suitability Ranker")
    cov_cols = [c for c in feats.columns if c.endswith("_cov")]
    real_pct = 100 * float(feats[cov_cols].to_numpy().mean()) if cov_cols else 0.0
    if is_synth or real_pct == 0:
        st.error("SYNTHETIC DATA - no real LOLA / Diviner / Chandrayaan-2 data is loaded. "
                 "Rankings are illustrative only and must not be read as real site recommendations.")
    elif real_pct < 100:
        st.warning(f"PARTLY SYNTHETIC - {real_pct:.0f}% of feature values are real; the rest are synthetic placeholders. "
                   "Per-site confidence shows how much of each score rests on real data.")
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
    df["landing"] = weighted_score(norm, weights["landing"])
    df["resource"] = weighted_score(norm, weights["resource"])
    df["eligible"] = passes_constraints(feats, cfg["constraints"])
    if hide:
        df.loc[~df.eligible, "landing"] = np.nan
    df["combined"] = (1 - mix) * df.landing + mix * df.resource  # NaN if either is NaN
    top = pick_top(df, view, top_n, min_sep_m=5000)
    sel_key = "selected_cell"

    left, right = st.columns([3, 2], gap="large")
    with left:
        # Read the picker's own key: it already holds this run's choice, so the ring
        # never lags one click behind (sel_key is only set further down the script).
        st.plotly_chart(heatmap(df, view, cell_m, top, st.session_state.get("site_pick"), view_name),
                        **_STRETCH)
        st.caption("Red markers = top-N sites (min 5 km apart). Cyan ring = site selected on the right. Map binned to ~5 km.")

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
            site_card(feats, df, norm, cid, weights, cfg)

    st.divider()
    st.subheader("Landing / ice pairs")
    pairs_table(df, top, cfg, feats)


def site_card(feats, df, norm, cid, weights, cfg) -> None:
    i = feats.index[feats.cell_id == cid][0]
    row, srow = feats.loc[i], df.loc[i]
    m = st.columns(3)
    m[0].metric("Landing", "-" if pd.isna(srow.landing) else f"{srow.landing:.0f}")
    m[1].metric("Resource", "-" if pd.isna(srow.resource) else f"{srow.resource:.0f}")
    m[2].metric("Combined", "-" if pd.isna(srow.combined) else f"{srow.combined:.0f}")
    allw = {**weights["landing"], **weights["resource"]}
    p, lab = confidence(row, allw)
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
                           marker_color=["#2a9d8f" if g == "landing" else "#e9c46a" for g in t.group],
                           hovertemplate="%{y}: %{x:.1f} pts<extra></extra>"))
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0), xaxis_title="points contributed to group score (teal = landing, gold = resource)",
                      yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, **_STRETCH)
    show = t.drop(columns=["contribution", "group"]).round(3)
    show["real data"] = show["real data"].map({True: "real", False: "SYNTHETIC / none"})
    st.dataframe(show, **_STRETCH, hide_index=True)


def pairs_table(df, top, cfg, feats) -> None:
    pairs = load_pairs()
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
    if dcol:
        pairs = pairs.sort_values(dcol)
    st.dataframe(pairs.round(3), **_STRETCH, hide_index=True, height=320)
    st.caption(f"{len(pairs):,} pairs, pairing radius {cfg['pairing']['radius_km']} km. "
               "Pairs come from P2's pairs.parquet; landing_score_live updates with the sliders.")


if __name__ == "__main__":
    main()
