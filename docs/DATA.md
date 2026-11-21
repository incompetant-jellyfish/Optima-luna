# Data

All data lives in `data/` and is **not** committed (see `.gitignore`).
Raw downloads go in `data/raw/<layer>/`; processed 1 km products go in `data/processed/`.

## Grid and projection

- South polar stereographic, pole at (0, 0), metres, on a 1737.4 km sphere
  (`config.yaml → grid.crs`). This matches the NASA PGDA LOLA polar DEMs.
- Square 1 km cells; a cell is kept if its centre is at or south of 80°S.
  That gives 290,364 cells (projected area; real area 288,139 km²).

## Layers and where to get them

| Layer | Product | Archive | Status |
|---|---|---|---|
| Elevation → slope, roughness, Earth visibility | LOLA south pole DEM, 20 m/px, 80–90°S | NASA PGDA, https://pgda.gsfc.nasa.gov/products/90 | TODO download |
| Illumination | LOLA polar illumination maps (Mazarico et al. 2011, Icarus 211) | PDS LOLA node, https://imbrium.mit.edu/BROWSE/EXTRAS/ILLUMINATION | TODO download |
| Temperature, cold traps | Diviner Polar Resource Product (annual mean / max temperature) | PDS Geosciences Node | TODO download |
| Ice signature (CPR) | Chandrayaan-2 DFSAR Level-3C polar mosaics | ISRO ISSDC PRADAN, https://pradan.issdc.gov.in/ch2 (registration) | TODO |
| Hydration | Chandrayaan-2 IIRS | ISRO ISSDC PRADAN (registration) | TODO |
| Thermal check point | Chandrayaan-3 ChaSTE | ISRO ISSDC PRADAN, https://pradan.issdc.gov.in/ch3 | TODO: confirm ChaSTE files are listed |
| Boulders | Chandrayaan-2 OHRC | ISRO ISSDC PRADAN | Not used in v1 (patchy coverage) |

PRADAN has no public API. Files are downloaded by hand after registering; loaders read
them from `data/raw/`. We never scrape or bypass authentication.

## Resampling rule

TODO (P1): document how each layer is brought onto the 1 km grid, e.g. mean slope and
max slope of the 20 m pixels inside each cell, area-weighted mean for coarser layers.

## Synthetic data

If a layer is missing, `src/synth.py` fills it with synthetic values. Synthetic values
have `<feature>_cov = False`, and every output that uses them is labelled **SYNTHETIC**.
