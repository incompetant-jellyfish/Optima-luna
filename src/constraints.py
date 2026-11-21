"""Phase 3a: hard landing constraints.

A cell fails if any *available* value breaks a limit in config.yaml → constraints:
mean slope, roughness or boulder density too high. A missing value (NaN) never fails
a cell: we don't throw away terrain just because a layer doesn't cover it. Missing
data shows up in the confidence score instead (see scoring.py).
"""

import numpy as np
import pandas as pd

from src.config import load_config

# feature column -> key of its limit in config.yaml → constraints
LIMITS = {
    "slope_mean": "slope_mean_max_deg",
    "roughness": "roughness_max_deg",
    "boulder_density": "boulder_density_max",
}


def landing_mask(features: pd.DataFrame, cfg: dict | None = None) -> pd.Series:
    """True where a cell passes every hard landing constraint it has data for."""
    cons = (cfg or load_config())["constraints"]
    ok = np.ones(len(features), dtype=bool)
    for col, key in LIMITS.items():
        if col in features:
            values = pd.to_numeric(features[col], errors="coerce").to_numpy(float)
            ok &= ~(values > cons[key])          # NaN > x is False, so NaN never fails
    return pd.Series(ok, index=features.index, name="eligible")


def failed_constraints(row: pd.Series, cfg: dict | None = None) -> list[str]:
    """Names of the limits one cell breaks, for the dashboard's site card."""
    cons = (cfg or load_config())["constraints"]
    return [col for col, key in LIMITS.items()
            if col in row and pd.notna(row[col]) and float(row[col]) > cons[key]]
