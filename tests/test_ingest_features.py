"""Ingest + features: checked on small GeoTIFFs with known answers (no real data needed)."""

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from src.config import feature_names, load_config
from src.features import build_features, coverage_report, features_version
from src.grid import build_grid, grid_spec
from src.ingest.lola import dem_slope_stats
from src.ingest.raster import resample_to_grid

SPEC = grid_spec()


def write_tif(path, data, x0, y0, res):
    with rasterio.open(path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1],
                       count=1, dtype="float32", crs=SPEC.crs,
                       transform=from_origin(x0, y0, res, res), nodata=-9999) as dst:
        dst.write(data.astype("float32"), 1)


def plane_dem(path, x0, y0, res=20.0, ncell=6, slope_deg=5.0):
    n = int(ncell * 1000 / res) + 7          # a few extra pixels -> partial cells at edges
    xs = x0 + (np.arange(n) + 0.5) * res
    z = np.tile(np.tan(np.radians(slope_deg)) * xs, (n, 1))
    write_tif(path, z, x0, y0, res)


@pytest.mark.parametrize("offset_m", [0.0, 260.0])     # aligned, and misaligned by 13 px
def test_plane_slope_recovered(tmp_path, offset_m):
    x0, y0 = -10000.0 + offset_m, 10000.0 - offset_m
    plane_dem(tmp_path / "dem.tif", x0, y0)
    out = dem_slope_stats(tmp_path / "dem.tif", SPEC)
    sm = out["slope_mean"]
    filled = np.isfinite(sm)
    assert filled.sum() >= 25
    assert np.allclose(sm[filled], 5.0, atol=1e-6)
    assert np.allclose(out["slope_max"][filled], 5.0, atol=1e-6)
    assert np.allclose(out["roughness"][filled], 0.0, atol=1e-3)   # float32 DEM noise
    # Filled cells sit where the DEM is: grid col of x=-10000 is (x - x_min)/1000.
    rows, cols = np.nonzero(filled)
    first_col = int(np.ceil((x0 - SPEC.x_min) / 1000 - 1e-9))
    first_row = int(np.ceil((SPEC.y_max - y0) / 1000 - 1e-9))
    assert cols.min() == first_col and rows.min() == first_row


def test_rough_terrain_has_roughness(tmp_path):
    x0, y0, res, n = -4000.0, 4000.0, 20.0, 200
    rng = np.random.default_rng(0)
    z = rng.normal(0, 5, (n, n))                        # bumpy
    write_tif(tmp_path / "dem.tif", z, x0, y0, res)
    out = dem_slope_stats(tmp_path / "dem.tif", SPEC)
    filled = np.isfinite(out["slope_mean"])
    assert (out["roughness"][filled] > 1).all()
    assert (out["slope_max"][filled] >= out["slope_mean"][filled]).all()


def test_illumination_average_and_psr(tmp_path):
    # 100 m pixels, columns alternate 0% / 60% lit -> mean 30%, half the pixels in shadow.
    n = 60
    data = np.tile(np.array([0.0, 60.0]), (n, n // 2))
    write_tif(tmp_path / "illum.tif", data, -3000.0, 3000.0, 100.0)
    frac = resample_to_grid(tmp_path / "illum.tif", scale=0.01, spec=SPEC)
    psr = resample_to_grid(tmp_path / "illum.tif", scale=0.01, spec=SPEC,
                           binary_fn=lambda v: v <= 1e-6)
    inner = np.isfinite(frac)
    assert inner.sum() == 36
    assert np.allclose(frac[inner], 0.30, atol=1e-6)
    assert np.allclose(psr[inner], 0.50, atol=1e-6)


# ---- features.py ------------------------------------------------------------------
def fake_synth(grid, cfg):
    df = grid[["cell_id"]].copy()
    for f in feature_names():
        df[f] = 1.0
        df[f"{f}_cov"] = False
    return df


def test_features_fill_gaps_and_flag_coverage():
    grid = build_grid()
    real_slope = np.full(len(grid), np.nan)
    real_slope[:100] = 3.0
    df = build_features(synth_fn=fake_synth, real={"slope_mean": real_slope})
    assert len(df) == len(grid)
    assert df["slope_mean_cov"].sum() == 100
    assert (df.loc[:99, "slope_mean"] == 3.0).all()
    assert (df.loc[100:, "slope_mean"] == 1.0).all()          # gap filled by synthetic
    assert not df["ice_cpr_cov"].any()
    assert df["features_version"].iloc[0] == "v1-lola"
    rep = coverage_report(df).set_index("feature")
    assert rep.loc["slope_mean", "real_%"] > 0 and rep.loc["ice_cpr", "real_%"] == 0


def test_features_version_labels():
    assert features_version({}) == "v0-synthetic"
    assert features_version({"slope_mean": 1}) == "v1-lola"
    assert features_version({"slope_mean": 1, "temp_max": 1}) == "v2-lola-diviner"


def test_file_scale_factor_applied(tmp_path):
    """NASA AVGVISIB stores int16 DN with scale 0.00004 (DN 25000 = fully visible)."""
    from src.ingest.lola import _illum_scale
    path = tmp_path / "avgvisib.tif"
    data = np.tile(np.array([0, 15000], dtype="int16"), (30, 15))      # 0 and 0.6 visible
    with rasterio.open(path, "w", driver="GTiff", height=30, width=30, count=1, dtype="int16",
                       crs=SPEC.crs, transform=from_origin(-3000.0, 3000.0, 100.0, 100.0),
                       nodata=-32768) as dst:
        dst.write(data, 1)
        dst.scales = (4e-5,)
    assert _illum_scale(path) == 1.0                    # file scale used, no percent guess
    frac = resample_to_grid(path, valid_range=(0, 1), spec=SPEC)
    inner = np.isfinite(frac)
    assert inner.sum() == 9
    assert np.allclose(frac[inner], 0.30, atol=1e-6)
