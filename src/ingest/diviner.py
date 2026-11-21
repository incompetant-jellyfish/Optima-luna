"""Diviner ingest: annual mean / max surface temperature on the 1 km grid.

Reads the LRO Diviner Polar Resource Product (PRP) rasters configured in
config.yaml → ingest (diviner_tmean, diviner_tmax) and averages them into cells.
Temperatures outside 20–450 K are treated as no-data.
"""

from src.config import ROOT, load_config
from src.grid import build_grid, grid_spec
from src.ingest.raster import raster_to_cells, resample_to_grid, write_layer

VALID_K = (20.0, 450.0)


def ingest_diviner(cfg: dict | None = None) -> list[str]:
    cfg = cfg or load_config()
    paths = cfg.get("ingest", {}) or {}
    grid, spec = build_grid(cfg), grid_spec(cfg)
    written = []
    for name, key in (("temp_mean", "diviner_tmean"), ("temp_max", "diviner_tmax")):
        p = paths.get(key)
        if p and (ROOT / p).exists():
            arr = resample_to_grid(ROOT / p, valid_range=VALID_K, spec=spec)
            write_layer(name, grid, raster_to_cells(grid, arr), f"Diviner PRP {p}", cfg)
            written.append(name)
        else:
            print(f"Diviner {key} not found ({p!r}) — {name} stays synthetic")
    return written


if __name__ == "__main__":
    print("Wrote layers:", ingest_diviner() or "none")
