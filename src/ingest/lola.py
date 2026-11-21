"""LOLA ingest: slope, roughness, illumination and permanent shadow on the 1 km grid.

DEM -> slope_mean, slope_max, roughness
---------------------------------------
The NASA PGDA south-pole DEM is 20 m/px over 80–90°S: about 30,000 x 30,000 pixels,
several GB. We never load it whole. We read it in horizontal bands aligned to the
1 km grid, with a 1-pixel halo so slopes at band edges are correct, and for each band:

  1. slope per pixel = atan(|∇z|), from np.gradient with the pixel spacing
  2. reshape into blocks of (1000 m / pixel size)^2 pixels — one block per grid cell
  3. per cell: slope_mean = mean, slope_max = max, roughness = std of pixel slopes

This needs the DEM in the same polar stereographic projection as the grid (true for
the PGDA products) and a pixel size that divides 1000 m (20 m -> 50 x 50 per cell).

Illumination -> illum_frac, psr_frac
------------------------------------
LOLA average-illumination maps are averaged into each cell (illum_frac). psr_frac is
the fraction of a cell's pixels whose average illumination is zero, i.e. permanently
shadowed. Percent maps (values up to 100) are converted to fractions automatically.

Run:  make ingest   (reads file paths from config.yaml → ingest)
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window

from src.config import ROOT, load_config
from src.grid import GridSpec, build_grid, grid_spec
from src.ingest.raster import raster_to_cells, resample_to_grid, write_layer

PSR_ILLUM_MAX = 1e-6  # average illumination at or below this counts as permanently shadowed


def _check_crs(crs, spec: GridSpec) -> None:
    """The DEM must use the grid's projection. Compared numerically: the same CRS can be
    written differently (e.g. `+lat_ts=-90` vs `+k=1`), so we project test points both
    ways and require agreement to a millimetre."""
    src, dst = CRS.from_user_input(crs), CRS.from_proj4(spec.crs)
    if src.equals(dst, ignore_axis_order=True):
        return
    t = Transformer.from_crs(src, dst, always_xy=True)
    xs = np.array([0.0, 100_000.0, -250_000.0, 300_000.0])
    ys = np.array([0.0, -50_000.0, 200_000.0, 10_000.0])
    x2, y2 = t.transform(xs, ys)
    if not (np.allclose(x2, xs, atol=1e-3) and np.allclose(y2, ys, atol=1e-3)):
        raise ValueError("DEM is not in the grid's south polar stereographic projection "
                         f"(DEM CRS: {src.to_wkt()[:120]}...). Reproject it first or ask P1.")


def dem_slope_stats(path: str | Path, spec: GridSpec | None = None,
                    band_cells: int = 8) -> dict[str, np.ndarray]:
    """Per-cell slope_mean, slope_max, roughness (degrees) as (nrows, ncols) arrays."""
    spec = spec or grid_spec()
    size = spec.cell_size_m
    out = {k: np.full((spec.nrows, spec.ncols), np.nan) for k in ("slope_mean", "slope_max", "roughness")}

    with rasterio.open(path) as src:
        _check_crs(src.crs, spec)
        t = src.transform
        res = t.a
        if not np.isclose(-t.e, res) or t.b or t.d:
            raise ValueError("DEM must have square, north-up pixels")
        block = size / res
        if not np.isclose(block, round(block)):
            raise ValueError(f"pixel size {res} m does not divide the {size} m cell size")
        block = int(round(block))

        # First pixel column/row that starts on a grid-cell edge.
        x0, y0 = t.c, t.f
        first_edge_x = spec.x_min + np.ceil((x0 - spec.x_min) / size - 1e-9) * size
        first_edge_y = spec.y_max - np.ceil((spec.y_max - y0) / size - 1e-9) * size
        px0 = int(round((first_edge_x - x0) / res))
        py0 = int(round((y0 - first_edge_y) / res))
        gc0 = int(round((first_edge_x - spec.x_min) / size))     # grid col of px0
        gr0 = int(round((spec.y_max - first_edge_y) / size))     # grid row of py0
        ncell_x = min((src.width - px0) // block, spec.ncols - gc0)
        ncell_y = min((src.height - py0) // block, spec.nrows - gr0)
        if ncell_x <= 0 or ncell_y <= 0:
            raise ValueError("DEM does not overlap the grid")
        nodata = src.nodata

        for cy in range(0, ncell_y, band_cells):
            nby = min(band_cells, ncell_y - cy)
            row_off = py0 + cy * block
            # 1-pixel halo above/below/left/right where the DEM has it.
            top = 1 if row_off > 0 else 0
            bottom = 1 if row_off + nby * block < src.height else 0
            left = 1 if px0 > 0 else 0
            right = 1 if px0 + ncell_x * block < src.width else 0
            win = Window(px0 - left, row_off - top, ncell_x * block + left + right,
                         nby * block + top + bottom)
            z = src.read(1, window=win).astype("float64")
            if nodata is not None:
                z[z == nodata] = np.nan
            dzdy, dzdx = np.gradient(z, res)
            slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
            slope = slope[top:top + nby * block, left:left + ncell_x * block]
            blocks = slope.reshape(nby, block, ncell_x, block)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)   # all-NaN blocks -> NaN
                rows = slice(gr0 + cy, gr0 + cy + nby)
                cols = slice(gc0, gc0 + ncell_x)
                out["slope_mean"][rows, cols] = np.nanmean(blocks, axis=(1, 3))
                out["slope_max"][rows, cols] = np.nanmax(blocks, axis=(1, 3))
                out["roughness"][rows, cols] = np.nanstd(blocks, axis=(1, 3))
    return out


def _illum_scale(path: str | Path) -> float:
    """1.0 for fraction maps, 0.01 for percent maps (decided from a sample)."""
    with rasterio.open(path) as src:
        sample = src.read(1, out_shape=(1, min(512, src.height), min(512, src.width))).astype(float)
        if src.nodata is not None:
            sample[sample == src.nodata] = np.nan
    return 0.01 if np.nanmax(sample) > 1.5 else 1.0


def ingest_lola(cfg: dict | None = None) -> list[str]:
    """Write every LOLA layer whose file is configured and present. Returns layer names."""
    cfg = cfg or load_config()
    paths = cfg.get("ingest", {}) or {}
    grid = build_grid(cfg)
    spec = grid_spec(cfg)
    written = []

    dem = paths.get("lola_dem")
    if dem and (ROOT / dem).exists():
        print(f"LOLA DEM: {dem} (windowed; this can take a few minutes)")
        stats = dem_slope_stats(ROOT / dem, spec)
        for name, arr in stats.items():
            write_layer(name, grid, raster_to_cells(grid, arr), f"LOLA DEM {dem}", cfg)
            written.append(name)
    else:
        print(f"LOLA DEM not found ({dem!r}) — slope layers stay synthetic")

    illum = paths.get("lola_illum")
    if illum and (ROOT / illum).exists():
        print(f"LOLA illumination: {illum}")
        scale = _illum_scale(ROOT / illum)
        frac = resample_to_grid(ROOT / illum, scale=scale, valid_range=(0, 1), spec=spec)
        psr = resample_to_grid(ROOT / illum, scale=scale, valid_range=(0, 1), spec=spec,
                               binary_fn=lambda v: v <= PSR_ILLUM_MAX)
        write_layer("illum_frac", grid, raster_to_cells(grid, frac), f"LOLA illumination {illum}", cfg)
        write_layer("psr_frac", grid, raster_to_cells(grid, psr), f"LOLA illumination {illum}", cfg)
        written += ["illum_frac", "psr_frac"]
    else:
        print(f"LOLA illumination not found ({illum!r}) — illum/psr stay synthetic")
    return written


if __name__ == "__main__":
    names = ingest_lola()
    print("Wrote layers:", names or "none")
