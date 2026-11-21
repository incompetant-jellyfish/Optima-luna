"""Reads P2's committed outputs in results/ for the dashboard.

Pure pandas/numpy (no Streamlit) so it can be unit-tested. Every reader is
defensive: a missing or unreadable file never crashes the app, it just comes
back as None (plus a warning string) and the app falls back to synthetic data.

Expected files (all scores 0-1):
  predictions.parquet  cell_id, landing_score, resource_score, landing_uncertainty,
                       resource_uncertainty, confidence, features_version
  pairs.parquet        landing_cell_id, ice_cell_id, distance_km, route_cost,
                       landing_score, resource_score, confidence, combined_score
  validation.csv       one row per known site (name, lat, lon, rank, in-top-K flag ...)
  metrics.json         R2 for MLP vs baseline, features_version ...
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

TRUE = {"true", "1", "yes", "y", "t"}


def load_results(results_dir: Path) -> dict:
    """Return {predictions, pairs, validation, metrics, version, warnings}."""
    out = {"predictions": None, "pairs": None, "validation": None, "metrics": None,
           "version": None, "warnings": []}
    readers = {
        "predictions": ("predictions.parquet", pd.read_parquet),
        "pairs": ("pairs.parquet", pd.read_parquet),
        "validation": ("validation.csv", pd.read_csv),
        "metrics": ("metrics.json", lambda p: json.loads(Path(p).read_text())),
    }
    for key, (fname, fn) in readers.items():
        p = Path(results_dir) / fname
        if not p.exists():
            continue
        try:
            out[key] = fn(p)
        except Exception as e:  # corrupted / half-written file
            out["warnings"].append(f"Could not read results/{fname} ({type(e).__name__}); ignoring it.")

    pred = out["predictions"]
    if pred is not None and "cell_id" not in pred:
        out["warnings"].append("results/predictions.parquet has no cell_id column; ignoring it.")
        out["predictions"] = pred = None
    if pred is not None and "features_version" in pred and len(pred):
        vers = pred["features_version"].dropna().astype(str).unique()
        out["version"] = vers[0] if len(vers) else None
        if len(vers) > 1:
            out["warnings"].append(f"predictions.parquet mixes features_version values: {list(vers)}")
    if out["version"] is None and isinstance(out["metrics"], dict):
        v = out["metrics"].get("features_version")
        out["version"] = None if v is None else str(v)
    return out


def version_is_synthetic(version: str | None) -> bool:
    """Rule from the P3 brief: features_version starting with v0 means synthetic."""
    return version is not None and str(version).strip().lower().startswith("v0")


def polar_xy(lat_deg, lon_deg, radius_m: float):
    """South-polar stereographic (same sphere/projection as config.yaml), metres."""
    colat = np.radians(90.0 + np.asarray(lat_deg, float))
    r = 2 * radius_m * np.tan(colat / 2)
    lon = np.radians(np.asarray(lon_deg, float))
    return r * np.sin(lon), r * np.cos(lon)


def _pick(cols, *cands):
    for c in cands:
        if c in cols:
            return c
    return None


def validation_points(val: pd.DataFrame | None, feats: pd.DataFrame | None, radius_m: float,
                      lat_limit_deg: float) -> pd.DataFrame:
    """Normalise validation.csv into x, y, name, rank, in_top, k, hover for the map.
    Column names are matched loosely because the file's exact layout isn't fixed."""
    cols = ["name", "x", "y", "rank", "in_top", "k", "hover"]
    if val is None or len(val) == 0:
        return pd.DataFrame(columns=cols)
    v = val.copy()
    v.columns = [str(c).strip().lower() for c in v.columns]
    name_c = _pick(v.columns, "name", "site", "label", "candidate", "site_name")
    if name_c is None:
        obj = [c for c in v.columns if v[c].dtype == object]
        name_c = obj[0] if obj else None
    lat_c, lon_c = _pick(v.columns, "lat", "latitude"), _pick(v.columns, "lon", "longitude", "lng")
    rank_c = _pick(v.columns, "rank", "site_rank", "rank_n")

    flag_c = k_c = None
    for c in v.columns:
        if "top" not in c or c == rank_c:
            continue
        vals = set(v[c].dropna().astype(str).str.strip().str.lower())
        if vals <= TRUE | {"false", "0", "no", "n", "f"}:
            flag_c = flag_c or c
        elif pd.api.types.is_numeric_dtype(v[c]):
            k_c = k_c or c

    out = pd.DataFrame({"name": v[name_c].astype(str) if name_c else [f"site {i+1}" for i in range(len(v))]})
    if lat_c and lon_c:
        out["x"], out["y"] = polar_xy(v[lat_c], v[lon_c], radius_m)
        inside = pd.to_numeric(v[lat_c], errors="coerce") <= lat_limit_deg  # grid only covers 80-90S
    elif "cell_id" in v and feats is not None:
        m = v[["cell_id"]].merge(feats[["cell_id", "x", "y"]], on="cell_id", how="left")
        out["x"], out["y"] = m["x"].to_numpy(), m["y"].to_numpy()
        inside = pd.Series(True, index=v.index)
    else:
        return pd.DataFrame(columns=cols)

    out["rank"] = pd.to_numeric(v[rank_c], errors="coerce") if rank_c else np.nan
    out["in_top"] = v[flag_c].astype(str).str.strip().str.lower().isin(TRUE) if flag_c else None
    if k_c:
        out["k"] = v[k_c]
    elif flag_c and re.search(r"\d+", flag_c):
        out["k"] = int(re.search(r"\d+", flag_c).group())
    else:
        out["k"] = np.nan

    def hover(r):
        k = "K" if pd.isna(r.k) else int(r.k)
        rk = "n/a" if pd.isna(r["rank"]) else int(r["rank"])
        it = "n/a" if r.in_top is None or pd.isna(r.in_top) else ("yes" if r.in_top else "no")
        return f"{r['name']}<br>rank {rk}, in top-{k}: {it}"

    out["hover"] = out.apply(hover, axis=1)
    out = out[inside.to_numpy() & out.x.notna().to_numpy() & out.y.notna().to_numpy()]
    return out[cols].reset_index(drop=True)


def flatten_metrics(m) -> pd.DataFrame:
    """metrics.json -> two-column table (metric, value), nested keys joined by '.'."""
    if not isinstance(m, dict):
        return pd.DataFrame(columns=["metric", "value"])
    flat = pd.json_normalize(m, sep=".").iloc[0]
    return pd.DataFrame({"metric": flat.index, "value": [str(x) for x in flat.values]})


def r2_items(m, limit: int = 4) -> list[tuple[str, float]]:
    """Numeric metrics whose key mentions r2 (e.g. mlp.r2, baseline.r2)."""
    if not isinstance(m, dict):
        return []
    flat = pd.json_normalize(m, sep=".").iloc[0]
    items = [(k, float(v)) for k, v in flat.items()
             if "r2" in k.lower().replace("²", "2") and isinstance(v, (int, float, np.floating)) and pd.notna(v)]
    return items[:limit]