import numpy as np
import pandas as pd
from src.validate import validate_reference_sites
from src.grid import lonlat_to_xy
from src.config import load_config


def test_reference_site_nearest_cell_and_top_k():
    cfg = load_config()
    refs = cfg["validation"]["reference_sites"]
    site = refs["shackleton_rim_r04"]
    x, y = lonlat_to_xy(site["lon_east_deg"], site["lat_deg"], cfg)
    frame = pd.DataFrame({"cell_id": [11, 12, 13], "x": [x, x+1000, x+2000],
                          "y": [y, y, y], "lat": [-89.7668]*3,
                          "lon": [-171.87]*3, "landing_score": [.9, .8, .7]})
    result = validate_reference_sites(frame, top_k=1, cfg=cfg)
    row = result.set_index("reference").loc["shackleton_rim_r04"]
    assert row.nearest_cell_id == 11
    assert bool(row.in_top_k)
    assert row.offset_to_cell_centre_m == 0
