"""Tests for app/results_io.py (reads P2's results/ files)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from results_io import (load_results, polar_xy, r2_items, validation_points,  # noqa: E402
                        version_is_synthetic)

R = 1737400


def test_missing_dir_is_fine(tmp_path):
    res = load_results(tmp_path / "nope")
    assert res["predictions"] is None and res["pairs"] is None and res["version"] is None


def test_version_rule():
    assert version_is_synthetic("v0-synthetic") and version_is_synthetic("V0")
    assert not version_is_synthetic("v1-real") and not version_is_synthetic(None)


def test_corrupt_file_warns_not_crashes(tmp_path):
    (tmp_path / "metrics.json").write_text("not json")
    res = load_results(tmp_path)
    assert res["metrics"] is None and res["warnings"]


def test_predictions_version_and_metrics(tmp_path):
    pd.DataFrame({"cell_id": [1, 2], "landing_score": [.1, .2], "features_version": "v1"}).to_parquet(
        tmp_path / "predictions.parquet")
    (tmp_path / "metrics.json").write_text(json.dumps({"mlp": {"r2": .9}, "baseline": {"r2": .8}}))
    res = load_results(tmp_path)
    assert res["version"] == "v1"
    assert dict(r2_items(res["metrics"])) == {"mlp.r2": .9, "baseline.r2": .8}


def test_polar_xy_pole_and_radius():
    x, y = polar_xy(-90, 0, R)
    assert abs(x) < 1e-6 and abs(y) < 1e-6
    x, y = polar_xy(-80, 0, R)           # 80S -> ~304 km from the pole
    assert abs(np.hypot(x, y) - 304_000) < 2_000


def test_validation_points_drops_outside_grid_and_formats_hover():
    v = pd.DataFrame({"name": ["Shackleton rim", "Chandrayaan-3"], "lat": [-89.9, -69.4], "lon": [129, 32],
                      "rank": [12, 9999], "in_top_10": ["no", "yes"]})
    out = validation_points(v, None, R, -80)
    assert list(out.name) == ["Shackleton rim"]            # 69S is outside 80-90S
    assert "rank 12, in top-10: no" in out.hover[0]