"""Phase 3b: landing safety and resource value scores. The one scoring definition.

model.py (pseudo-labels), pairing.py and the dashboard all import from here, so a
change to the scoring rule happens in exactly one place.

How a score is computed
-----------------------
1. normalise(): each feature is clipped to its 2nd–98th percentile over the whole
   region and rescaled to 0–1, flipped where "lower is better" so 1 is always good.
   Percentiles (not min/max) stop a few extreme pixels from squashing everything else.
2. weighted(): weighted mean of the normalised features a cell actually has.
   Missing features (NaN) are skipped and the remaining weights are renormalised —
   we never invent a value for a missing layer.
3. confidence: share of the total weight that is backed by *real* data
   (value present AND <feature>_cov is True). Synthetic values can produce a score
   but never raise confidence.

All scores and confidences are in [0, 1]. The dashboard multiplies by 100 for display.
"""

import numpy as np
import pandas as pd

from src.config import load_config
from src.constraints import landing_mask

PCT_LO, PCT_HI = 2, 98
GROUPS = ("landing", "resource")


def default_weights(cfg: dict | None = None) -> dict[str, dict[str, float]]:
    """{'landing': {feature: weight}, 'resource': {...}} from config.yaml."""
    sc = (cfg or load_config())["scoring"]
    return {g: {f: float(spec["weight"]) for f, spec in sc[g].items()} for g in GROUPS}


def normalise(features: pd.DataFrame, cfg: dict | None = None) -> pd.DataFrame:
    """0–1 'goodness' per scored feature (1 = better). NaN stays NaN.

    Independent of the weights, so callers (the dashboard) can cache it and only
    re-run weighted() when sliders move.
    """
    sc = (cfg or load_config())["scoring"]
    out = {}
    for group in GROUPS:
        for f, spec in sc[group].items():
            if f not in features or f in out:
                continue
            v = pd.to_numeric(features[f], errors="coerce").to_numpy(float)
            finite = np.isfinite(v)
            if not finite.any():
                out[f] = np.full(len(v), np.nan)
                continue
            lo, hi = np.percentile(v[finite], [PCT_LO, PCT_HI])
            n = np.clip((v - lo) / (hi - lo), 0, 1) if hi > lo else np.where(finite, 0.5, np.nan)
            if spec["direction"] == "lower":
                n = 1 - n
            elif spec["direction"] != "higher":
                raise ValueError(f"unknown direction {spec['direction']!r} for {f}")
            out[f] = n
    return pd.DataFrame(out, index=features.index)


def weighted(norm: pd.DataFrame, weights: dict[str, float],
             coverage: pd.DataFrame | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Score and confidence for one group (e.g. weights = default_weights()['landing']).

    norm      output of normalise()
    weights   {feature: weight}; weights <= 0 are ignored
    coverage  any frame holding <feature>_cov columns (usually the features table);
              None means no data counts as real, so confidence is 0
    """
    n = len(norm)
    num, den, real = np.zeros(n), np.zeros(n), np.zeros(n)
    total = sum(w for w in weights.values() if w > 0)
    for f, w in weights.items():
        if w <= 0 or f not in norm:
            continue
        v = norm[f].to_numpy(float)
        ok = np.isfinite(v)
        num[ok] += v[ok] * w
        den[ok] += w
        cov_col = f"{f}_cov"
        if coverage is not None and cov_col in coverage:
            is_real = coverage[cov_col].fillna(False).astype(bool).to_numpy() & ok
            real[is_real] += w
    with np.errstate(invalid="ignore", divide="ignore"):
        score = np.where(den > 0, num / den, np.nan)
    confidence = real / total if total > 0 else np.zeros(n)
    return score, confidence


def score(features: pd.DataFrame, cfg: dict | None = None,
          weights: dict[str, dict[str, float]] | None = None) -> pd.DataFrame:
    """Full scoring table, one row per cell, same index as `features`.

    Columns: cell_id, landing_score, resource_score, landing_confidence,
    resource_confidence, confidence (mean of the two), eligible (passes hard
    landing constraints). Ineligible cells keep their landing_score so the model can
    learn it; filter on `eligible` when picking landing sites.
    """
    cfg = cfg or load_config()
    weights = weights or default_weights(cfg)
    norm = normalise(features, cfg)
    out = pd.DataFrame(index=features.index)
    if "cell_id" in features:
        out["cell_id"] = features["cell_id"]
    for group in GROUPS:
        s, c = weighted(norm, weights[group], features)
        out[f"{group}_score"] = s
        out[f"{group}_confidence"] = c
    out["confidence"] = (out["landing_confidence"] + out["resource_confidence"]) / 2
    out["eligible"] = landing_mask(features, cfg)
    return out


def contributions(norm_row: pd.Series, weights: dict[str, float]) -> pd.Series:
    """Each feature's share of one cell's group score (sums to the score).

    Exact for a weighted mean: share = weight × goodness / sum of available weights.
    """
    avail = {f: w for f, w in weights.items() if w > 0 and f in norm_row and pd.notna(norm_row[f])}
    den = sum(avail.values())
    return pd.Series({f: (w * norm_row[f] / den if den else np.nan) for f, w in avail.items()})


if __name__ == "__main__":
    from src.config import ROOT
    path = ROOT / load_config()["paths"]["processed"] / "features.parquet"
    if not path.exists():
        raise SystemExit(f"{path} not found — run `make features` first")
    feats = pd.read_parquet(path)
    s = score(feats)
    print(s.describe().round(3).to_string())
    print(f"Eligible for landing: {s['eligible'].mean():.1%} of cells")
