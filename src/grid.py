"""Phase 1: the polar grid every other module works on.

What it does
------------
Projects the lunar south pole to polar stereographic (metres, pole at 0,0) and lays a
regular square grid over it (default 1 km cells). A cell is kept when its centre lies
at or south of the latitude limit (default 80°S). Each cell gets:

    cell_id  stable integer id (row * ncols + col)
    row,col  position in the full square raster, so any column can be turned back
             into a 2-D image with `to_raster` (for heatmaps and resampling)
    x, y     cell centre in projected metres
    lat, lon cell centre in degrees

Why this projection
-------------------
NASA PGDA's LOLA polar DEMs use the same polar stereographic projection on a
1737.4 km sphere, so LOLA rasters line up with this grid without reprojection.

Note on area: stereographic stretches distances away from the pole (scale factor
~1.008 at 80°S), so a 1 km x 1 km projected cell covers slightly less real ground
near the edge. `true_area_km2` holds the real area of each cell.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer

from src.config import load_config

# Geographic coordinates on the same lunar sphere as the projection.
def _geo_crs(radius_m: float) -> CRS:
    return CRS.from_proj4(f"+proj=longlat +R={radius_m} +no_defs")


@dataclass(frozen=True)
class GridSpec:
    cell_size_m: float
    half_extent_m: float   # grid covers [-half_extent, +half_extent] in x and y
    nrows: int
    ncols: int
    crs: str
    radius_m: float

    @property
    def x_min(self) -> float:
        return -self.half_extent_m

    @property
    def y_max(self) -> float:
        return self.half_extent_m


def _transformers(crs: str, radius_m: float) -> tuple[Transformer, Transformer]:
    proj = CRS.from_proj4(crs)
    geo = _geo_crs(radius_m)
    to_xy = Transformer.from_crs(geo, proj, always_xy=True)
    to_ll = Transformer.from_crs(proj, geo, always_xy=True)
    return to_xy, to_ll


def lonlat_to_xy(lon, lat, cfg: dict | None = None):
    cfg = cfg or load_config()
    to_xy, _ = _transformers(cfg["grid"]["crs"], cfg["moon"]["radius_m"])
    return to_xy.transform(lon, lat)


def xy_to_lonlat(x, y, cfg: dict | None = None):
    cfg = cfg or load_config()
    _, to_ll = _transformers(cfg["grid"]["crs"], cfg["moon"]["radius_m"])
    return to_ll.transform(x, y)


def grid_spec(cfg: dict | None = None) -> GridSpec:
    cfg = cfg or load_config()
    g, radius = cfg["grid"], cfg["moon"]["radius_m"]
    size = float(g["cell_size_m"])
    # Distance from the pole to the latitude limit in projected metres.
    _, y_edge = lonlat_to_xy(0.0, g["lat_limit_deg"], cfg)
    rho = abs(y_edge)
    n = int(np.ceil(rho / size))          # cells from the pole to the edge
    return GridSpec(size, n * size, 2 * n, 2 * n, g["crs"], radius)


def build_grid(cfg: dict | None = None) -> pd.DataFrame:
    """Return one row per cell inside the latitude limit."""
    cfg = cfg or load_config()
    spec = grid_spec(cfg)
    s = spec.cell_size_m

    cols = np.arange(spec.ncols)
    rows = np.arange(spec.nrows)
    xc = spec.x_min + (cols + 0.5) * s            # centres, west -> east
    yc = spec.y_max - (rows + 0.5) * s            # centres, north -> south (image order)
    X, Y = np.meshgrid(xc, yc)
    R, C = np.meshgrid(rows, cols, indexing="ij")

    lon, lat = xy_to_lonlat(X.ravel(), Y.ravel(), cfg)
    lat = np.asarray(lat)
    keep = lat <= cfg["grid"]["lat_limit_deg"]

    df = pd.DataFrame({
        "cell_id": (R.ravel() * spec.ncols + C.ravel())[keep].astype(np.int64),
        "row": R.ravel()[keep].astype(np.int32),
        "col": C.ravel()[keep].astype(np.int32),
        "x": X.ravel()[keep],
        "y": Y.ravel()[keep],
        "lat": lat[keep],
        "lon": np.asarray(lon)[keep],
    })
    # Polar stereographic (tangent at the south pole) scale factor: k = 2 / (1 + sin|lat|).
    k = 2.0 / (1.0 + np.sin(np.radians(np.abs(df["lat"].to_numpy()))))
    df["true_area_km2"] = (s / 1000.0) ** 2 / k**2
    return df.reset_index(drop=True)


def cap_area_km2(lat_limit_deg: float, radius_m: float) -> float:
    """Exact area of the polar cap from the pole to lat_limit on a sphere."""
    colat = np.radians(90.0 - abs(lat_limit_deg))
    r_km = radius_m / 1000.0
    return 2.0 * np.pi * r_km**2 * (1.0 - np.cos(colat))


def to_raster(grid: pd.DataFrame, values, spec: GridSpec | None = None,
              fill=np.nan) -> np.ndarray:
    """Put a per-cell column back into the full 2-D square (NaN outside the cap)."""
    spec = spec or grid_spec()
    out = np.full((spec.nrows, spec.ncols), fill, dtype=float)
    out[grid["row"].to_numpy(), grid["col"].to_numpy()] = np.asarray(values, dtype=float)
    return out


if __name__ == "__main__":
    cfg = load_config()
    spec = grid_spec(cfg)
    grid = build_grid(cfg)
    cap = cap_area_km2(cfg["grid"]["lat_limit_deg"], cfg["moon"]["radius_m"])
    print(f"Raster: {spec.nrows} x {spec.ncols} at {spec.cell_size_m:.0f} m, "
          f"half extent {spec.half_extent_m / 1000:.0f} km")
    print(f"Cells kept: {len(grid):,}")
    print(f"Cap area (exact): {cap:,.0f} km²; sum of true cell areas: "
          f"{grid['true_area_km2'].sum():,.0f} km²")
    print(f"Lat range: {grid['lat'].min():.3f} to {grid['lat'].max():.3f}")
