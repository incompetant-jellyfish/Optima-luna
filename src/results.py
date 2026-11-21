"""Write the slim, committed results/ folder the dashboard and judges read.

data/ and models/ are git-ignored; results/ is not. Run after model, pairs, validate:

    make results          (or: make train  = model + pairs + validate + results)

results/predictions.parquet  cell_id, landing_score, resource_score, landing_uncertainty,
                             resource_uncertainty, confidence (float32), features_version
results/pairs.parquet        pairing output (unchanged)
results/metrics.json         models/metrics.json incl. features_version, train_seconds
results/validation.csv       already written there by src/validate.py
"""

import json
import shutil

import pandas as pd

from src.config import ROOT, load_config

PRED_COLS = ["cell_id", "landing_score", "resource_score", "landing_uncertainty",
             "resource_uncertainty", "confidence"]


def export_results(cfg: dict | None = None) -> list[str]:
    cfg = cfg or load_config()
    processed = ROOT / cfg["paths"]["processed"]
    out = ROOT / "results"
    out.mkdir(exist_ok=True)

    scored = pd.read_parquet(processed / "scored_features.parquet")
    missing = [c for c in PRED_COLS if c not in scored]
    if missing:
        raise SystemExit(f"scored_features.parquet lacks {missing}: run `make model` first")
    metrics = json.loads((ROOT / "models" / "metrics.json").read_text())
    version = metrics.get("features_version") or (
        str(scored["features_version"].iloc[0]) if "features_version" in scored else "unknown")
    if "features_version" in scored and str(scored["features_version"].iloc[0]) != version:
        raise SystemExit("models/metrics.json and scored_features.parquet come from different runs: "
                         "re-run `make model`")

    pred = scored[PRED_COLS].copy()
    pred["cell_id"] = pred["cell_id"].astype("int64")
    for c in PRED_COLS[1:]:
        pred[c] = pred[c].astype("float32")
    pred["features_version"] = version
    pred.to_parquet(out / "predictions.parquet", index=False)

    shutil.copyfile(processed / "pairs.parquet", out / "pairs.parquet")
    metrics["features_version"] = version
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    if not (out / "validation.csv").exists():
        raise SystemExit("results/validation.csv missing: run `make validate`")
    return sorted(p.name for p in out.iterdir())


if __name__ == "__main__":
    files = export_results()
    sizes = {f: f"{(ROOT / 'results' / f).stat().st_size / 1e6:.1f} MB" for f in files}
    print("Wrote results/:", sizes)
