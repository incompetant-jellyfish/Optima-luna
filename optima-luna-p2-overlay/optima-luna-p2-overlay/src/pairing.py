"""Rank nearby landing-site/resource-site pairs using transparent local costs."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from src.config import ROOT, load_config


def _haversine_km(lat1, lon1, lat2, lon2, radius_km=1737.4):
    """Great-circle distance on the configured lunar sphere."""
    a1, a2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(lon2 - lon1)
    dp = a2 - a1
    h = np.sin(dp / 2) ** 2 + np.cos(a1) * np.cos(a2) * np.sin(dl / 2) ** 2
    return 2 * radius_km * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def _score_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    for name in candidates:
        if name in frame.columns:
            return name
    raise ValueError(f"input needs one of these score columns: {candidates}")


def rank_pairs(
    features: pd.DataFrame,
    *,
    radius_km: float | None = None,
    top_n: int | None = None,
    cfg: dict | None = None,
) -> pd.DataFrame:
    """For every landing candidate, choose the best eligible resource candidate.

    A Euclidean KD-tree on the existing polar-stereographic x/y grid finds candidates
    within radius. Distances reported in output are great-circle lunar distances.
    Route-cost v1 = distance_km * mean endpoint slope in degrees. This is a simple
    heuristic, not a traversability analysis or a path planner.
    """
    cfg = cfg or load_config()
    radius = float(radius_km if radius_km is not None else cfg["pairing"]["radius_km"])
    limit = int(top_n if top_n is not None else cfg["pairing"]["top_n"])
    if radius <= 0 or limit <= 0:
        raise ValueError("radius_km and top_n must be positive")
    required = {"cell_id", "x", "y", "lat", "lon", "slope_mean"}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"features missing columns: {sorted(missing)}")
    landing_score = _score_column(features, ("landing_score", "landing_pred", "landing"))
    resource_score = _score_column(features, ("resource_score", "resource_pred", "resource"))
    frame = features.copy().reset_index(drop=True)
    for col in (landing_score, resource_score, "slope_mean", "x", "y"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    valid_landing = frame[landing_score].notna() & frame[["x", "y", "slope_mean"]].notna().all(axis=1)
    valid_resource = frame[resource_score].notna() & frame[["x", "y"]].notna().all(axis=1)
    land = frame.loc[valid_landing].copy()
    resource = frame.loc[valid_resource].copy()
    if land.empty or resource.empty:
        return pd.DataFrame(columns=["landing_cell_id", "ice_cell_id", "distance_km", "route_cost", "landing_score", "resource_score", "confidence", "combined_score"])
    tree = cKDTree(resource[["x", "y"]].to_numpy(float))
    radius_m = radius * 1000.0
    rows = []
    # Query all landing coordinates in one compiled KD-tree call rather than making
    # hundreds of thousands of Python -> C transitions on the full 290k-cell grid.
    nearby_by_landing = tree.query_ball_point(land[["x", "y"]].to_numpy(float), r=radius_m * 1.02)
    for (_, site), nearby_indices in zip(land.iterrows(), nearby_by_landing):
        if not nearby_indices:
            continue
        candidates = resource.iloc[nearby_indices].copy()
        # Exclude pairing a cell with itself; same-cell pairing is not a useful transfer.
        candidates = candidates.loc[candidates.cell_id != site.cell_id]
        if candidates.empty:
            continue
        candidates["distance_km"] = _haversine_km(
            float(site.lat), float(site.lon), candidates.lat.to_numpy(float), candidates.lon.to_numpy(float),
            float(cfg["moon"]["radius_m"]) / 1000.0,
        )
        candidates = candidates.loc[candidates.distance_km <= radius]
        if candidates.empty:
            continue
        mean_slope = (float(site.slope_mean) + pd.to_numeric(candidates.slope_mean, errors="coerce").fillna(float(site.slope_mean))) / 2
        candidates["route_cost"] = candidates.distance_km * mean_slope
        # Pair quality prefers high scores, then low route cost. Normalised to [0, 1].
        route_norm = candidates.route_cost / max(radius * 30.0, 1e-9)
        candidates["combined_score"] = (0.5 * site[landing_score] + 0.5 * candidates[resource_score]) * (1 - np.clip(route_norm, 0, 1))
        if "landing_confidence" in frame and "resource_confidence" in frame:
            landing_conf = float(pd.to_numeric(pd.Series([site["landing_confidence"]]), errors="coerce").fillna(0).iloc[0])
            resource_conf = pd.to_numeric(candidates["resource_confidence"], errors="coerce").fillna(0)
            conf = (landing_conf + resource_conf) / 2
        elif "confidence" in frame:
            landing_conf = float(pd.to_numeric(pd.Series([site["confidence"]]), errors="coerce").fillna(0).iloc[0])
            resource_conf = pd.to_numeric(candidates["confidence"], errors="coerce").fillna(0)
            conf = (landing_conf + resource_conf) / 2
        else:
            conf = pd.Series(0.0, index=candidates.index)
        candidates["_confidence"] = conf.clip(0, 1)
        best = candidates.sort_values(["combined_score", "route_cost"], ascending=[False, True]).iloc[0]
        rows.append({
            "landing_cell_id": int(site.cell_id), "ice_cell_id": int(best.cell_id),
            "distance_km": float(best.distance_km), "route_cost": float(best.route_cost),
            "landing_score": float(site[landing_score]), "resource_score": float(best[resource_score]),
            "confidence": float(best["_confidence"]), "combined_score": float(best.combined_score),
        })
    output_columns = ["landing_cell_id", "ice_cell_id", "distance_km", "route_cost",
                      "landing_score", "resource_score", "confidence", "combined_score"]
    result = pd.DataFrame(rows, columns=output_columns)
    if result.empty:
        return result
    return result.sort_values(["combined_score", "route_cost"], ascending=[False, True]).head(limit).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/scored_features.parquet")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/pairs.parquet")
    args = parser.parse_args()
    data = pd.read_parquet(args.input)
    pairs = rank_pairs(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pairs.to_parquet(args.output, index=False)
    print(f"Wrote {len(pairs)} pairs to {args.output}")

if __name__ == "__main__": main()
