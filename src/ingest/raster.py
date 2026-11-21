"""Shared raster helpers: put any georeferenced raster onto the 1 km grid.

`resample_to_grid` warps a raster (any CRS GDAL understands, any resolution) onto the
grid's 610 x 610 polar stereographic raster with *average* resampling, i.e. each 1 km
cell gets the area-weighted mean of the source pixels it covers. Used for coarser or
similar-resolution layers (illumination, Diviner temperature).

The 20 m LOLA DEM is handled separately in lola.py: we need slope statistics per
cell (mean / max / std), which averaging the elevations would destroy.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

from src.config import ROOT, load_config
from src.grid import GridSpec, grid_spec


def grid_transform(spec: GridSpec):
    return from_origin(spec.x_min, spec.y_max, spec.cell_size_m, spec.cell_size_m)


def resample_to_grid(path: str | Path, *, band: int = 1, scale: float = 1.0,
                     valid_range: tuple[float, float] | None = None,
                     spec: GridSpec | None = None,
                     binary_fn=None) -> np.ndarray:
    """Average the raster at `path` into grid cells. Returns a (nrows, ncols) float array.

    scale        multiply values after reading (e.g. 0.01 for percent -> fraction)
    valid_range  values outside are treated as no-data
    binary_fn    optional f(values) -> 0/1 array; the result is then the *fraction* of
                 each cell where it is 1 (used for permanent-shadow fraction)
    """
    spec = spec or grid_spec()
    with rasterio.open(path) as src:
        data = src.read(band).astype("float64")
        if src.nodata is not None:
            data[data == src.nodata] = np.nan
        # Apply the file's own scale/offset (e.g. LOLA illumination: DN × 0.00004).
        data = data * src.scales[band - 1] + src.offsets[band - 1]
        data *= scale
        if valid_range is not None:
            lo, hi = valid_range
            data[(data < lo) | (data > hi)] = np.nan
        if binary_fn is not None:
            finite = np.isfinite(data)
            data = np.where(finite, binary_fn(np.where(finite, data, 0)).astype("float64"), np.nan)
        out = np.full((spec.nrows, spec.ncols), np.nan)
        reproject(source=data, destination=out,
                  src_transform=src.transform, src_crs=src.crs,
                  dst_transform=grid_transform(spec), dst_crs=spec.crs,
                  src_nodata=np.nan, dst_nodata=np.nan,
                  resampling=Resampling.average)
    return out


def raster_to_cells(grid: pd.DataFrame, arr: np.ndarray) -> np.ndarray:
    """Pick each grid cell's value out of a (nrows, ncols) array."""
    return arr[grid["row"].to_numpy(), grid["col"].to_numpy()]


def layers_dir(cfg: dict | None = None) -> Path:
    cfg = cfg or load_config()
    return ROOT / cfg["paths"]["processed"] / "layers"


def write_layer(name: str, grid: pd.DataFrame, values: np.ndarray, source: str,
                cfg: dict | None = None) -> Path:
    """Save one real feature layer as data/processed/layers/<name>.parquet."""
    out = layers_dir(cfg)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.parquet"
    df = pd.DataFrame({"cell_id": grid["cell_id"].to_numpy(),
                       "value": np.asarray(values, dtype="float32")})
    df.attrs["source"] = source
    df.to_parquet(path, index=False)
    (out / f"{name}.source.txt").write_text(source + "\n")
    return path
