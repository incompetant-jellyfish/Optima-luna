"""Phase 1 acceptance: cell count matches the area within 2%; lat/lon round-trips."""

import numpy as np
import pytest

from src.config import load_config
from src.grid import (build_grid, cap_area_km2, grid_spec, lonlat_to_xy,
                      to_raster, xy_to_lonlat)


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def grid(cfg):
    return build_grid(cfg)


def test_cell_count_matches_area_within_2pct(cfg, grid):
    cap = cap_area_km2(cfg["grid"]["lat_limit_deg"], cfg["moon"]["radius_m"])
    cell_km2 = (cfg["grid"]["cell_size_m"] / 1000) ** 2
    expected = cap / cell_km2
    assert abs(len(grid) - expected) / expected < 0.02


def test_true_area_sums_to_cap_area(cfg, grid):
    cap = cap_area_km2(cfg["grid"]["lat_limit_deg"], cfg["moon"]["radius_m"])
    assert abs(grid["true_area_km2"].sum() - cap) / cap < 0.005


def test_all_cells_inside_limit(cfg, grid):
    assert (grid["lat"] <= cfg["grid"]["lat_limit_deg"]).all()
    assert grid["lat"].min() >= -90


def test_cell_ids_unique_and_match_row_col(grid):
    spec = grid_spec()
    assert grid["cell_id"].is_unique
    assert (grid["cell_id"] == grid["row"] * spec.ncols + grid["col"]).all()


def test_latlon_round_trip(cfg, grid):
    sample = grid.sample(2000, random_state=0)
    x, y = lonlat_to_xy(sample["lon"].to_numpy(), sample["lat"].to_numpy(), cfg)
    assert np.allclose(x, sample["x"], atol=1e-3)
    assert np.allclose(y, sample["y"], atol=1e-3)
    lon, lat = xy_to_lonlat(x, y, cfg)
    assert np.allclose(lat, sample["lat"], atol=1e-9)


def test_known_point_distance(cfg):
    # 80°S should sit ~304 km from the pole: 2R·tan(5°) on a 1737.4 km sphere.
    x, y = lonlat_to_xy(0.0, -80.0, cfg)
    expected = 2 * cfg["moon"]["radius_m"] * np.tan(np.radians(5))
    assert np.isclose(np.hypot(x, y), expected, rtol=1e-9)


def test_to_raster_round_trip(grid):
    img = to_raster(grid, grid["lat"])
    assert np.allclose(img[grid["row"], grid["col"]], grid["lat"])
    assert np.isnan(img).sum() == img.size - len(grid)
