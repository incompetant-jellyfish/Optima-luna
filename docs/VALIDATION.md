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
top-K.

### Result (features v1-lola, 22 Nov 2026, `results/validation.csv`)

Real layers: LOLA slope / roughness (40 m DEM), illumination and permanent shadow. Ice,
hydration, temperature, boulders, craters and Earth visibility are still SYNTHETIC.
Ranked by landing score over all 290,364 cells, top-K = 10.

| Reference | Nearest cell (offset) | Landing score | Rank | In top 10 | What pulled it down |
|---|---|---:|---:|:---:|---|
| Shackleton Rim R04 | 190623 (707 m) | 0.35 | 281,536 | No | **Fails the slope rule:** mean slope 30.6° (limit 10°). The rim is a narrow crest; a 1 km cell centred 707 m away is mostly the crater's inner wall. Illumination 0.21 also costs 0.14. |
| Malapert Massif R23 | 111934 (0.5 m) | 0.70 | 98,656 | No | Passes every rule (slope 7.1°). Loses most to roughness 3.0° (−0.09), slope (−0.08) and illumination 0.36 (−0.06). Good, not exceptional, at 1 km. |

**Verdict: both reference sites miss the top 10.** Honest reading: (1) at 1 km, a narrow
sunlit rim cannot be separated from the steep wall beside it, a resolution limit of our grid;
(2) Malapert is a reasonable but not top-ranked cell under our weights, which favour flatness
and sunlight over anything mission-specific (comms, traverse, science). NASA's regions also
weigh factors we don't model. This is a disagreement we report, not one we tune away.

Model (held-out 10 km spatial blocks, test split): landing R² Ridge 0.994 vs MLP 0.969
(with 15% of inputs hidden: 0.975 vs 0.904); resource R² MLP 0.987 vs Ridge 0.965 (hidden:
0.558 vs 0.425). The MLP helps on the resource score, not on landing. R² measures imitation of
our scoring rule, not landing accuracy.

## Known limitations / failures

- Only LOLA layers are real so far; ice, hydration, temperature, boulders, craters and Earth
  visibility are synthetic placeholders (confidence shows this per cell).
- 1 km cells average narrow features (crater rims) with their surroundings.
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
make ingest      # LOLA rasters in data/raw (scripts/download_data.py)
make features    # features.parquet (real layers + labelled synthetic fill)
make train       # model -> pairs -> validate -> results/
make test
```
