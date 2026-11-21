# Model and reference-site validation

## Data and model validity

This repository snapshot does not contain downloaded LOLA, Diviner, Chandrayaan-2 DFSAR,
IIRS, or OHRC observations. The synthetic generator creates spatially correlated **demo
fields** only. It is not an empirical lunar map and cannot validate actual ice deposits,
terrain hazards, landing safety, or mission feasibility.

The model's targets are weighted pseudo-labels computed from the project's feature scoring
rules. R²/MAE therefore describe agreement with that scoring heuristic on held-out spatial
blocks; they are not accuracy measures against ground observations. This distinction must
be retained in the PPT and demo. `*_cov` flags determine real-data confidence; synthetic
values can be used for a reproducible code demo but have false coverage flags and contribute
zero measured-data confidence.

`src.model.train_models` groups cells into projected-coordinate blocks (default 10 km),
then holds out entire groups for validation and test. Group overlap is checked. The baseline
is Ridge regression; the MLP has two hidden layers (64, 32). Both are evaluated with and
without random feature masking. Masking removes complete feature layers as well as a small
fraction of individual entries to emulate missing products and patchy coverage. The masked
MLP uses three independently seeded members by default. The ensemble mean is the prediction;
member standard deviation is a model-spread indicator, not a calibrated probability interval.

## Reference points and results

The NASA Lunar Surface Data Book (ACD-50044, Rev A, Appendix A2.1, Table A2-2) states that
its feature centre points were generated from PGDA DEMs and are accurate to 5–10 m. It gives:

| Reference | Reference definition | Latitude | Longitude (east-positive) | Source |
|---|---|---:|---:|---|
| Shackleton Rim | Representative named rim point, `R04 / Site04` | -89.7668° | -171.87° | [NASA Lunar Surface Data Book, Table A2-2](https://ntrs.nasa.gov/api/citations/20230007818/downloads/ACD-50044%20Lunar%20Surface%20Data%20Book%20Rev%20A.pdf) |
| Malapert Massif | Named massif representative point, `R23 / Site23` | -85.9948° | -0.23578° | [NASA Lunar Surface Data Book, Table A2-2](https://ntrs.nasa.gov/api/citations/20230007818/downloads/ACD-50044%20Lunar%20Surface%20Data%20Book%20Rev%20A.pdf) |

For comparison, the [USGS/IAU Gazetteer entry for Mons Malapert](https://planetarynames.wr.usgs.gov/Feature/16338) (feature ID 16338,
LOLA 2011 planetographic, east-positive longitude) gives a named-feature centre of
-85.98°, -1.67° and an approximate boundary spanning -85.15° to -86.40° latitude and
12.79°E to 16.12°W. Mons Malapert and the Artemis/NASA Malapert Massif representative point are related but not identical coordinate definitions.
NASA lists Malapert Massif among its 13 Artemis III candidate regions; this is not a claim of
final landing-site selection ([NASA candidate-region announcement](https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/)).

The coordinates are stored in `config.yaml` under `validation.reference_sites`. `src.validate`
transforms them onto the active polar grid, finds the nearest grid cell and reports distance
to cell centre, rank in the selected score column, and whether the nearest cell appears in
top-K. Run it against actual scored parquet artefacts to obtain the real rank result. No
real top-K outcome is asserted in this source document because no real feature/model outputs
were present when it was drafted.

## Known limitations / failures

- No real raster layers are bundled; empirical validation is blocked until data ingestion.
- Pairing cost is `straight-line distance × mean endpoint slope`. It is not a least-cost route
  and does not find a path around cliffs, craters, boulders, or no-data regions.
- KD-tree lookup selects nearby candidates in projected space; final radius filtering uses
  lunar great-circle distance. This is proximity matching, not route planning.
- Synthetic features have all `<feature>_cov = False`; they must not increase real-data
  confidence even though their pseudo-labels are usable for software testing.
- Ensemble spread is not calibrated uncertainty.
- Linear explanation is additive in transformed feature space. MLP explanations are
  one-feature perturbation effects, not SHAP values or causal contributions.
- Pseudo-labels depend on configured weights and percentile normalisation; the scores are
  policy-dependent.

## Reproduction

```bash
python -m src.synth
python -m src.model --input data/processed/features.parquet
python -m src.pairing --input data/processed/scored_features.parquet
python -m src.validate --input data/processed/scored_features.parquet
python -m pytest -q
```
