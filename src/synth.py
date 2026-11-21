"""Generate explicitly synthetic, spatially correlated lunar-south-pole features.

This is demo/test data, not a substitute for LOLA, Diviner, or Chandrayaan products.
The generator uses the shared grid and feature-column contract and writes a provenance
sidecar so downstream users can never mistake the output for measured observations.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter

from src.config import ROOT, feature_names, load_config
from src.grid import build_grid, grid_spec

SYNTHETIC_FEATURES = tuple(feature_names())


def _normalise(field: np.ndarray) -> np.ndarray:
    """Scale a finite array to [0, 1], safely handling constant arrays."""
    lo, hi = np.nanmin(field), np.nanmax(field)
    return np.zeros_like(field, dtype=float) if hi <= lo else (field - lo) / (hi - lo)


def generate_synthetic_features(
    grid: pd.DataFrame | None = None,
    *,
    seed: int = 20261121,
    missing_fraction: float = 0.08,
    cfg: dict | None = None,
) -> pd.DataFrame:
    """Create realistic-looking spatial fields on the project's 1 km polar grid.

    Shape relationships are intentional: slope rises around crater rims, cold traps
    occupy crater interiors/low terrain, and ice indicators are strongest in cold traps.
    Missing values are patchy and each feature has a ``<feature>_cov`` boolean column.
    All coverage flags are False because every value produced here is synthetic.
    """
    if not 0 <= missing_fraction < 1:
        raise ValueError("missing_fraction must be in [0, 1)")
    cfg = cfg or load_config()
    grid = build_grid(cfg) if grid is None else grid.copy()
    required = {"cell_id", "row", "col", "x", "y", "lat", "lon"}
    absent = required - set(grid.columns)
    if absent:
        raise ValueError(f"grid is missing required columns: {sorted(absent)}")
    if grid.empty:
        raise ValueError("cannot synthesize an empty grid")

    rng = np.random.default_rng(seed)
    spec = grid_spec(cfg)
    shape = (spec.nrows, spec.ncols)

    # Create a handful of deterministic crater-like bowls in projected coordinates.
    # Values are dimensionless terrain morphology, not geologic measurements.
    x = grid["x"].to_numpy(float)
    y = grid["y"].to_numpy(float)
    extent = max(float(np.nanmax(np.abs(np.r_[x, y]))), 1.0)
    centres = [(-0.42 * extent, -0.28 * extent, 0.105 * extent),
               (0.24 * extent, -0.51 * extent, 0.075 * extent),
               (0.48 * extent, 0.27 * extent, 0.095 * extent),
               (-0.18 * extent, 0.53 * extent, 0.065 * extent)]
    bowl = np.zeros(len(grid), dtype=float)
    rim = np.zeros(len(grid), dtype=float)
    for cx, cy, radius in centres:
        rr = np.hypot(x - cx, y - cy) / radius
        bowl += np.exp(-0.5 * (rr / 0.72) ** 2)
        rim += np.exp(-0.5 * ((rr - 1.0) / 0.13) ** 2)
    bowl = _normalise(bowl)
    rim = _normalise(rim)

    # Smooth correlated noise gives neighbouring cells coherent terrain variation.
    noise_raster = gaussian_filter(rng.normal(size=shape), sigma=7, mode="nearest")
    noise = noise_raster[grid["row"].to_numpy(int), grid["col"].to_numpy(int)]
    noise = (noise - noise.mean()) / (noise.std() + 1e-9)
    fine_noise = rng.normal(0, 1, len(grid))

    # Steep rims have elevated slope; bowl floors tend to be gentler than rim crests.
    slope_mean = np.clip(2.0 + 5.2 * rim - 1.15 * bowl + 0.55 * noise + 0.25 * fine_noise, 0.2, 18.0)
    slope_max = np.clip(slope_mean + 1.2 + 2.4 * rim + np.abs(fine_noise) * 0.8, slope_mean, 32.0)
    roughness = np.clip(0.6 + 2.5 * rim + 0.45 * np.abs(noise) + rng.normal(0, .2, len(grid)), 0.05, 9.0)

    # Cold traps are likely in low-illumination bowl interiors; rim exposure is warmer.
    psr_frac = np.clip(0.04 + 0.78 * bowl - 0.12 * rim + rng.normal(0, .045, len(grid)), 0, 1)
    illum_frac = np.clip(0.12 + 0.76 * (1 - bowl) - 0.26 * rim + rng.normal(0, .07, len(grid)), 0, 1)
    temp_max = np.clip(155 - 92 * psr_frac + 9 * illum_frac + rng.normal(0, 5, len(grid)), 35, 190)
    temp_mean = np.clip(105 - 54 * psr_frac + 7 * illum_frac + rng.normal(0, 4, len(grid)), 25, 155)

    # Ice proxies are correlated with cold trapping, but deliberately noisy and imperfect.
    ice_cpr = np.clip(0.12 + 0.72 * psr_frac + rng.normal(0, .12, len(grid)), 0, 1.5)
    hydration_depth = np.clip(0.025 + 0.16 * psr_frac + rng.normal(0, .025, len(grid)), 0, .35)
    crater_density = np.clip(3.5 + 8.0 * (0.35 * bowl + 0.65 * rim) + rng.normal(0, 1.8, len(grid)), 0, 30)
    boulder_density = np.clip(9 + 8 * rim + 1.6 * np.abs(noise) + rng.normal(0, 2, len(grid)), 0, 60)
    earth_los_frac = np.clip(0.42 + 0.18 * (1 - bowl) + rng.normal(0, .06, len(grid)), 0, 1)

    values = {
        "slope_mean": slope_mean, "slope_max": slope_max, "roughness": roughness,
        "boulder_density": boulder_density, "crater_density": crater_density,
        "illum_frac": illum_frac, "psr_frac": psr_frac, "temp_mean": temp_mean,
        "temp_max": temp_max, "ice_cpr": ice_cpr,
        "hydration_depth": hydration_depth, "earth_los_frac": earth_los_frac,
    }
    result = grid.copy()
    for name in feature_names():
        if name not in values:
            raise KeyError(f"synthetic generator has no recipe for configured feature {name!r}")
        column = np.asarray(values[name], dtype=float).copy()
        # Patchy spatial gaps: small missing blocks plus independent missing cells.
        if missing_fraction:
            independent = rng.random(len(column)) < missing_fraction * 0.55
            block_raster = gaussian_filter(rng.random(shape), sigma=10, mode="nearest")
            block_score = block_raster[result.row.to_numpy(int), result.col.to_numpy(int)]
            block_score = _normalise(block_score)
            patch = block_score < missing_fraction * 0.45
            column[independent | patch] = np.nan
        result[name] = column
        # Synthetic values are never counted as real data coverage.
        result[f"{name}_cov"] = False
    result["data_provenance"] = "SYNTHETIC"
    result["synthetic_seed"] = int(seed)
    return result


def write_synthetic_features(
    output: str | Path | None = None,
    *, seed: int = 20261121,
    missing_fraction: float = 0.08,
    cfg: dict | None = None,
) -> tuple[Path, Path]:
    """Write the feature Parquet and a provenance JSON sidecar."""
    cfg = cfg or load_config()
    output = Path(output or (ROOT / cfg["paths"]["processed"] / "features.parquet"))
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = generate_synthetic_features(seed=seed, missing_fraction=missing_fraction, cfg=cfg)
    # Parquet requires pyarrow or fastparquet. Fail with a direct install hint.
    try:
        frame.to_parquet(output, index=False)
    except ImportError as exc:
        raise RuntimeError("Writing Parquet requires pyarrow; install requirements.txt") from exc
    sidecar = output.with_suffix(output.suffix + ".metadata.json")
    metadata = {
        "provenance": "SYNTHETIC - NOT OBSERVED LUNAR DATA",
        "seed": seed,
        "rows": int(len(frame)),
        "missing_fraction_requested": missing_fraction,
        "coverage_semantics": "All *_cov values are False for synthetic values",
        "features": feature_names(),
        "warning": "Do not use these values as scientific evidence or mission-planning measurements.",
    }
    sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return output, sidecar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None, help="Output Parquet path")
    parser.add_argument("--seed", type=int, default=20261121)
    parser.add_argument("--missing-fraction", type=float, default=0.08)
    args = parser.parse_args()
    try:
        parquet, metadata = write_synthetic_features(args.output, seed=args.seed,
                                                      missing_fraction=args.missing_fraction)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"SYNTHETIC feature table: {parquet}")
    print(f"Provenance sidecar: {metadata}")
    print(f"Rows: {len(pd.read_parquet(parquet)):,}; features: {len(feature_names())}")


if __name__ == "__main__":
    main()
