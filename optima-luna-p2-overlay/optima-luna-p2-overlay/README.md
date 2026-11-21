# Lunar South Pole Site Suitability Ranker

ASTRA 2026 hackathon project. A decision-support prototype that divides the lunar south
polar region (80°S–90°S) into 1 km cells, scores cells for landing suitability and resource
potential, and ranks nearby landing/resource pairs. **It is not a final site selector or a
mission-certified hazard assessment.**

## P2 pipeline

1. `python -m src.synth` creates a spatially correlated synthetic feature table on the
   shared polar grid. Crater rims have steeper slopes, crater interiors/low terrain are
   colder and more shadowed, and ice indicators are correlated with cold traps. Missing
   patches are retained as NaNs. Outputs are marked `SYNTHETIC`; every synthetic
   `<feature>_cov` flag is False.
2. `python -m src.model` creates weighted pseudo-labels, evaluates a Ridge baseline and a
   two-hidden-layer MLP with and without random feature-layer masking, and holds out whole
   projected spatial blocks. It saves a three-member masked-MLP ensemble. Ensemble mean is
   the score estimate; member spread is a simple uncertainty indicator, not a calibrated
   interval.
3. `python -m src.pairing` pairs each landing candidate with a nearby resource candidate.
   Version 1 route cost is straight-line distance times mean endpoint slope. It is not a
   least-cost path or traversability guarantee.
4. `src.explain` provides additive contributions for compatible linear models and
   one-feature perturbation effects for nonlinear models. Perturbation effects are not
   SHAP values.
5. `python -m src.validate` compares nearest grid cells to source-cited Shackleton Rim and
   Malapert Massif reference points and reports score rank / top-K status.

## Setup and run

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m src.synth
python -m src.model --input data/processed/features.parquet
python -m src.pairing --input data/processed/scored_features.parquet
python -m src.validate --input data/processed/scored_features.parquet
python -m pytest -q
```

Parquet read/write requires the pinned `pyarrow` dependency. Model artefacts are written to
`models/`; `data/` and `models/` are excluded from Git.

## Interpreting metrics honestly

Training targets are the configured weighted-score heuristic, not ground-truth labels.
Therefore R²/MAE measure how well a model approximates that scoring rule on held-out spatial
blocks. They do **not** demonstrate real-world landing accuracy, ice abundance, safety, or
mission success. Read `models/metrics.json` alongside the config.

## Data and validation

Real data products and download notes: [docs/DATA.md](docs/DATA.md). Validation protocol,
reference coordinate sources, and known failures: [docs/VALIDATION.md](docs/VALIDATION.md).
Synthetic data is solely a development/demo fallback. It must not be described as observed
lunar terrain or used as scientific measurement.

## Credits

See [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) and [AI_USAGE.md](AI_USAGE.md).
