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
| Elevation → slope, roughness | LOLA south pole DEM `LDEM_80S_40MPP_ADJ.TIF`, 40 m/px, 80–90°S (20 m version too slow to fetch) | NASA PGDA, https://pgda.gsfc.nasa.gov/products/90 | downloading |
| Illumination, permanent shadow, Earth visibility | LOLA `AVGVISIB_75S_120M_201608` (+ `_EARTH`, `LPSR_75S_120M_201608`), 120 m/px (Mazarico et al. 2011, Icarus 211) | NASA PGDA, https://pgda.gsfc.nasa.gov/products/69 | illumination ingested; PSR / Earth downloading |
| Temperature, cold traps | Diviner Polar Resource Product (annual mean / max temperature) | PDS Geosciences Node (`dlre_prp_south.tab`, 605 MB table) | TODO: download + table→grid ingest |
| Ice signature (CPR) | Chandrayaan-2 DFSAR Level-3C polar mosaics | ISRO ISSDC PRADAN, https://pradan.issdc.gov.in/ch2 (registration) | TODO |
| Hydration | Chandrayaan-2 IIRS | ISRO ISSDC PRADAN (registration) | TODO |
| Thermal check point | Chandrayaan-3 ChaSTE | ISRO ISSDC PRADAN, https://pradan.issdc.gov.in/ch3 | TODO: confirm ChaSTE files are listed |
| Boulders | Chandrayaan-2 OHRC | ISRO ISSDC PRADAN | Not used in v1 (patchy coverage) |

PRADAN has no public API. Files are downloaded by hand after registering; loaders read
them from `data/raw/`. We never scrape or bypass authentication.

## Resampling rule

Every layer ends up as one value per 1 km cell (`data/processed/layers/<feature>.parquet`).

| Feature | Rule | Code |
|---|---|---|
| `slope_mean`, `slope_max`, `roughness` | From the 20 m LOLA DEM: slope per pixel = atan(\|∇z\|) using central differences; then per cell (50 × 50 pixels) the **mean**, **max** and **standard deviation** of pixel slopes. The DEM is read in 1 km-aligned bands with a 1-pixel halo, so it's never loaded whole (~30 s, ~0.6 GB RAM for 80–90°S). Pixels that only partly fill a cell at the DEM edge are dropped. | `src/ingest/lola.py` |
| `illum_frac` | LOLA average-illumination map, **area-weighted mean** per cell (GDAL average resampling). Percent maps are converted to fractions. | `src/ingest/lola.py` |
| `psr_frac` | **Fraction of the cell's pixels** whose average illumination is 0 (permanently shadowed). | `src/ingest/lola.py` |
| `temp_mean`, `temp_max` | Diviner PRP rasters, **area-weighted mean** per cell; values outside 20–450 K are treated as no-data. | `src/ingest/diviner.py` |
| everything else | No real layer in v1, so filled from `src/synth.py` with `_cov = False`. | `src/features.py` |

Requirement: the DEM must be in the grid's south polar stereographic projection (the
PGDA products are). This is checked numerically, so the same projection written a
different way is accepted. Other layers can be in any CRS GDAL reads; they are warped.

File paths go in `config.yaml → ingest`. Then: `make ingest && make features`.
The output's `features_version` column says what's real: `v0-synthetic`, `v1-lola` or
`v2-lola-diviner`.

## Synthetic data

If a layer is missing, `src/synth.py` fills it with synthetic values. Synthetic values
have `<feature>_cov = False`, and every output that uses them is labelled **SYNTHETIC**.

Download everything with `python3 scripts/download_data.py` (resumable; parallel connections
because NASA PGDA throttles each one to ~15 KB/s). Sources are logged to `data/raw/SOURCES.txt`.
