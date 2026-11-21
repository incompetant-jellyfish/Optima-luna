import numpy as np
import pandas as pd
from src.synth import generate_synthetic_features


def tiny_grid():
    rows, cols = np.indices((80, 80))
    return pd.DataFrame({"cell_id": np.arange(rows.size), "row": rows.ravel(), "col": cols.ravel(),
                        "x": (cols.ravel() - 40) * 1000.0, "y": (40 - rows.ravel()) * 1000.0,
                        "lat": -85.0, "lon": np.linspace(-180, 180, rows.size)})


def test_synth_contract_deterministic_and_provenance():
    grid = tiny_grid()
    a = generate_synthetic_features(grid, seed=7)
    b = generate_synthetic_features(grid, seed=7)
    pd.testing.assert_frame_equal(a, b)
    assert set(a.data_provenance) == {"SYNTHETIC"}
    for name in ["slope_mean", "psr_frac", "ice_cpr", "temp_max"]:
        assert f"{name}_cov" in a
        assert not a[f"{name}_cov"].any()
        assert a[name].isna().any()


def test_synth_physical_correlations():
    data = generate_synthetic_features(tiny_grid(), seed=11, missing_fraction=0)
    assert data.loc[data.psr_frac > .65, "ice_cpr"].mean() > data.loc[data.psr_frac < .2, "ice_cpr"].mean()
    assert data.loc[data.psr_frac > .65, "temp_max"].mean() < data.loc[data.psr_frac < .2, "temp_max"].mean()
    assert data.slope_mean.max() > data.slope_mean.median() * 1.5


def test_invalid_missing_fraction_rejected():
    import pytest
    with pytest.raises(ValueError):
        generate_synthetic_features(tiny_grid(), missing_fraction=1.0)


def test_crater_rims_are_steeper_than_bowls_and_bowls_are_colder():
    grid = tiny_grid()
    data = generate_synthetic_features(grid, seed=12, missing_fraction=0)
    extent = max(float(np.nanmax(np.abs(np.r_[grid.x, grid.y]))), 1.0)
    cx, cy, radius = -0.42 * extent, -0.28 * extent, 0.105 * extent
    radial = np.hypot(grid.x.to_numpy() - cx, grid.y.to_numpy() - cy) / radius
    rim = np.abs(radial - 1.0) < 0.12
    bowl = radial < 0.55
    assert data.loc[rim, "slope_mean"].mean() > data.loc[bowl, "slope_mean"].mean()
    assert data.loc[bowl, "psr_frac"].mean() > data.loc[radial > 1.4, "psr_frac"].mean()
    assert data.loc[bowl, "temp_max"].mean() < data.loc[radial > 1.4, "temp_max"].mean()
