"""Phase 2: build data/processed/features.parquet, the table everything else reads.

For each feature in the config.yaml contract:
  * if a real layer exists in data/processed/layers/<feature>.parquet (written by
    src/ingest/*), use it: <feature>_cov = True where the value is present;
  * otherwise, or where the real layer has gaps, use P2's synthetic generator
    (src/synth.py): <feature>_cov = False.

So every cell has a value for every feature, and the _cov columns say exactly which
values are real. A `features_version` column records what went in:
  v0-synthetic       no real layers
  v1-lola            LOLA layers (slope/roughness and/or illumination)
  v2-lola-diviner    LOLA + Diviner temperatures
A JSON sidecar next to the parquet repeats the version and the coverage report.

Run:  make features
"""

import json

import numpy as np
import pandas as pd

from src.config import ROOT, feature_names, load_config
from src.grid import build_grid
from src.ingest.raster import layers_dir

LOLA_LAYERS = {"slope_mean", "slope_max", "roughness", "illum_frac", "psr_frac"}
DIVINER_LAYERS = {"temp_mean", "temp_max"}


def _default_synth(grid: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    try:
        from src.synth import generate_synthetic_features   # P2's module
    except ImportError as exc:
        raise SystemExit("src/synth.py not found yet — P2 must move it out of the overlay "
                         "folder into src/ (see docs/tasks/P2.md step 1)") from exc
    return generate_synthetic_features(grid, cfg=cfg)


def load_real_layers(grid: pd.DataFrame, cfg: dict | None = None) -> dict[str, np.ndarray]:
    """{feature: values aligned to grid rows} for every real layer on disk."""
    d = layers_dir(cfg)
    real = {}
    for f in feature_names():
        p = d / f"{f}.parquet"
        if p.exists():
            layer = pd.read_parquet(p).set_index("cell_id")["value"]
            real[f] = layer.reindex(grid["cell_id"]).to_numpy(dtype="float64")
    return real


def features_version(real: dict) -> str:
    names = set(real)
    if names & DIVINER_LAYERS and names & LOLA_LAYERS:
        return "v2-lola-diviner"
    if names & LOLA_LAYERS:
        return "v1-lola"
    if names:
        return "v1-partial"
    return "v0-synthetic"


def build_features(cfg: dict | None = None, synth_fn=None,
                   real: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    grid = build_grid(cfg)
    real = load_real_layers(grid, cfg) if real is None else real
    synth = (synth_fn or _default_synth)(grid, cfg)
    synth = synth.set_index("cell_id").reindex(grid["cell_id"])

    df = grid.copy()
    for f in feature_names():
        fallback = synth[f].to_numpy(dtype="float64")
        if f in real:
            r = np.asarray(real[f], dtype="float64")
            has = np.isfinite(r)
            df[f] = np.where(has, r, fallback).astype("float32")
            df[f"{f}_cov"] = has
        else:
            df[f] = fallback.astype("float32")
            df[f"{f}_cov"] = False
    df["features_version"] = features_version(real)
    return df


def coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for f in feature_names():
        rows.append({"feature": f,
                     "real_%": round(100 * df[f"{f}_cov"].mean(), 3),
                     "missing_%": round(100 * df[f].isna().mean(), 3)})
    return pd.DataFrame(rows)


def main() -> None:
    cfg = load_config()
    df = build_features(cfg)
    out = ROOT / cfg["paths"]["processed"] / "features.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    rep = coverage_report(df)
    version = df["features_version"].iloc[0]
    meta = {"features_version": version, "rows": int(len(df)),
            "coverage": rep.to_dict(orient="records"),
            "note": "Values with <feature>_cov = False are SYNTHETIC placeholders."}
    out.with_suffix(".parquet.metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"Wrote {out} — {len(df):,} cells, version {version}")
    print(rep.to_string(index=False))
    if version == "v0-synthetic":
        print("\nALL FEATURES ARE SYNTHETIC — label every output SYNTHETIC.")


if __name__ == "__main__":
    main()
