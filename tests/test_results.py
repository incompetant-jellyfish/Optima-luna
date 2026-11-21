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

def test_validation_points_reads_validate_py_output():
    """Columns exactly as src/validate.py writes results/validation.csv."""
    val = pd.DataFrame({
        "reference": ["shackleton_rim_r04", "malapert_massif_r23"],
        "reference_lat_deg": [-89.7668, -85.9948], "reference_lon_east_deg": [-171.87, -0.23578],
        "nearest_cell_id": [190623, 111934], "nearest_cell_lat_deg": [-89.75, -85.99],
        "nearest_cell_lon_deg": [-168.7, -0.24], "score_column": ["landing_score"] * 2,
        "score": [0.5, 0.7], "rank": [265619, 53790], "in_top_k": [False, True], "top_k": [10, 10],
    })
    pts = validation_points(val, None, 1737400.0, -80.0)
    assert list(pts.name) == ["shackleton_rim_r04", "malapert_massif_r23"]
    assert list(pts.in_top) == [False, True] and list(pts.k) == [10, 10]
    assert pts[["x", "y"]].notna().all().all()
