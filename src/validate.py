"""Check named lunar reference points against a gridded score table.

Coordinates are east-positive, planetographic as stored in the project configuration.
The module reports point-to-cell-centre offset and ranks; it does not certify a site.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from src.config import ROOT, load_config
from src.grid import lonlat_to_xy


def validate_reference_sites(
    frame: pd.DataFrame,
    *,
    score_column: str = "landing_score",
    top_k: int = 10,
    cfg: dict | None = None,
) -> pd.DataFrame:
    """Find nearest grid cell and score rank for source-cited reference coordinates."""
    cfg = cfg or load_config()
    required = {"cell_id", "x", "y", score_column}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"input missing required columns: {sorted(missing)}")
    refs = cfg.get("validation", {}).get("reference_sites", {})
    if not refs:
        raise ValueError("config.yaml has no validation.reference_sites entries")
    ranked = frame.loc[pd.to_numeric(frame[score_column], errors="coerce").notna()].copy()
    ranked = ranked.sort_values(score_column, ascending=False).reset_index(drop=True)
    ranked["rank"] = ranked.index + 1
    rows = []
    for key, site in refs.items():
        lon, lat = float(site["lon_east_deg"]), float(site["lat_deg"])
        x, y = lonlat_to_xy(lon, lat, cfg)
        offsets = ((ranked.x.to_numpy(float) - x) ** 2 + (ranked.y.to_numpy(float) - y) ** 2) ** 0.5
        nearest_i = int(offsets.argmin())
        nearest = ranked.iloc[nearest_i]
        rows.append({
            "reference": key,
            "description": site.get("description", ""),
            "source": site.get("source", ""),
            "reference_lat_deg": lat,
            "reference_lon_east_deg": lon,
            "nearest_cell_id": int(nearest.cell_id),
            "nearest_cell_lat_deg": float(nearest.get("lat", float("nan"))),
            "nearest_cell_lon_deg": float(nearest.get("lon", float("nan"))),
            "offset_to_cell_centre_m": float(offsets[nearest_i]),
            "score_column": score_column,
            "score": float(nearest[score_column]),
            "rank": int(nearest["rank"]),
            "in_top_k": bool(nearest["rank"] <= top_k),
            "top_k": int(top_k),
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/scored_features.parquet")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/reference_validation.csv")
    parser.add_argument("--score-column", default="landing_score")
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()
    frame = pd.read_parquet(args.input)
    result = validate_reference_sites(frame, score_column=args.score_column, top_k=args.top_k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))

if __name__ == "__main__": main()
