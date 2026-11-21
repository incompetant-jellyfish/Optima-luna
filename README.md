# Lunar South Pole Site Suitability Ranker

**Live demo:** _link added after deploy_ · ASTRA 2026 hackathon project. A decision-support tool that divides 80°S–90°S on the Moon
into 1 km cells, scores each for landing safety and resource value, and pairs safe landing
cells with nearby ice. **It is decision support, not a final site selector or a
mission-certified hazard assessment.**

## Problem

Artemis and Chandrayaan missions target the lunar south pole: it has near-permanent sunlight
on some ridges and water-ice cold traps in permanently shadowed craters a few km away. The
data to choose a site exists (LOLA terrain and illumination, Diviner temperatures,
Chandrayaan-2 radar and spectra) but sits in different archives, projections and
resolutions, with patchy coverage. Comparing sites means stitching it by hand.

**Scope:** 80°S–90°S, 1 km cells, two questions per cell: *is it safe to land?* and *is it
worth going to for resources?*, then pair the two within driving distance.

## What it does

- **One grid, every layer:** 290,364 cells of 1 km in the same polar stereographic
  projection as NASA's LOLA products; each data source is resampled onto it.
- **Hard safety rules first:** cells with slope, roughness or boulder density above the
  limits in `config.yaml` are excluded from landing.
- **Transparent scores:** landing and resource scores are weighted means of normalised
  features. Weights are live sliders in the dashboard.
- **Honest confidence:** every score says what share of its weight rests on real data.
  Missing layers are never invented; synthetic placeholders are labelled SYNTHETIC.
- **Model:** an MLP ensemble trained to reproduce the score with whole layers randomly
  hidden, so it still ranks cells where a dataset is missing; Ridge regression baseline.
- **Landing ↔ ice pairs** within 10 km, with a simple route-cost heuristic.
- **Validation** against NASA-published reference points (Shackleton rim,
  Malapert massif; NASA Lunar Surface Data Book ACD-50044).

## Results

From `results/` (training 37 s on CPU; 62% of cells pass the landing rules). Details and the
why behind each miss: [docs/VALIDATION.md](docs/VALIDATION.md).

| | Value |
|---|---|
| Features version | v1-lola: real LOLA slope, roughness, illumination, shadow; rest synthetic |
| Held-out R², landing (MLP vs Ridge; with 15% inputs hidden) | 0.969 vs **0.994** (0.904 vs **0.975**) |
| Held-out R², resource (MLP vs Ridge; with 15% inputs hidden) | **0.987** vs 0.965 (**0.558** vs 0.425) |
| Shackleton rim R04: rank / in top 10 | 281,536 / no: its 1 km cell is mostly 30° crater wall |
| Malapert massif R23: rank / in top 10 | 98,656 / no: passes all rules, not top under our weights |

## Limitations

- Training targets are our own scoring rule, not ground truth (see below).
- Chandrayaan-2 DFSAR (ice) and IIRS (hydration) need ISSDC registration; where they are
  not loaded those layers are SYNTHETIC and confidence drops accordingly.
- Slope comes from the 40 m/px LOLA DEM: hazards smaller than ~40 m (boulders) are not
  resolved. OHRC boulder maps are not used in v1.
- Route cost is distance × mean slope, not a traverse plan.

## Impact

A first-pass screening tool: it narrows ~288,000 km² to a short, explainable list of
candidate landing/ice pairs, shows *why* each ranks where it does and how much of that rests
on real data, so mission planners spend detailed analysis time only where it matters.

## Setup and run

```bash
git clone https://github.com/incompetant-jellyfish/Optima-luna.git && cd Optima-luna
make setup      # create .venv and install pinned requirements
make test       # run the tests
make run        # start the dashboard: open the printed Local URL
```

Requires Python 3.11+. On NixOS the Makefile adds the needed system libraries automatically.
Without `make` (Windows): `python -m venv .venv`, `.venv\Scripts\pip install -r requirements.txt`,
`.venv\Scripts\streamlit run app/main.py`.

**The dashboard works straight after cloning:** the committed `results/` folder holds the
features table, model predictions, pairs, metrics and validation from our last run. You only
need the raw data to rebuild them.

## Pipeline

Rebuild everything from raw NASA data (~1.5 GB download, then ~2 minutes of compute):

```bash
python3 scripts/download_data.py --only illum dem   # NASA PGDA LOLA files -> data/raw/ (resumable)
make ingest     # rasters -> 1 km layers (slope/roughness from the 40 m DEM: ~15 s)
make features   # data/processed/features.parquet: real layers + SYNTHETIC fill, _cov flags
make scores     # landing / resource scores, confidence, hard-constraint mask
make train      # model (~40 s) -> pairs (~30 s) -> validate -> results/
```

Individual steps: `make grid`, `make model`, `make pairs`, `make validate`, `make results`.

| Step | Module | What it does |
|---|---|---|
| Grid | `src/grid.py` | Polar stereographic 1 km cells, same projection as NASA's LOLA polar DEMs |
| Ingest | `src/ingest/` | LOLA DEM → slope / roughness; illumination → sunlit and shadowed fraction; Diviner → temperatures |
| Features | `src/features.py`, `src/synth.py` | Real layers where available; spatially correlated SYNTHETIC values elsewhere (`_cov = False`) |
| Scoring | `src/constraints.py`, `src/scoring.py` | Hard landing rules; weighted 0–1 scores; confidence = share of weight backed by real data |
| Model | `src/model.py` | Weighted-score pseudo-labels; Ridge baseline and two-hidden-layer MLP with random feature-layer masking; whole spatial blocks held out; three-member ensemble spread as a simple (uncalibrated) uncertainty |
| Pairing | `src/pairing.py` | For each landing candidate, a nearby resource cell. v1 route cost = straight-line distance × mean endpoint slope: a heuristic, not a path planner |
| Explain | `src/explain.py`, `scoring.contributions` | Additive per-feature contributions; one-feature perturbation effects for the MLP (not SHAP values) |
| Validate | `src/validate.py` | Nearest cells to source-cited Shackleton Rim and Malapert Massif points; their rank and top-K status |
| Results | `src/results.py` | Slim, committed `results/`: predictions, pairs, metrics, validation, features |
| Dashboard | `app/main.py`, `app/results_io.py` | Heatmap with NASA reference sites, live weight sliders, site card with confidence and model ± spread, pairs table, model panel, SYNTHETIC/PARTLY SYNTHETIC banners |

## Interpreting metrics honestly

Training targets are the configured weighted-score rule, not ground-truth labels: no one
has labelled "good" landing sites. R² and MAE therefore measure how well a model
reproduces that rule on held-out spatial blocks, especially when layers are missing. They
do **not** show real-world landing accuracy, ice abundance, safety or mission success.

## Data and validation

Real data products, download notes and the resampling rule: [docs/DATA.md](docs/DATA.md).
Validation protocol, reference coordinate sources and known failures:
[docs/VALIDATION.md](docs/VALIDATION.md). Synthetic data is only a development and demo
fallback and is labelled SYNTHETIC wherever it appears.

## Repository layout

```
app/        Streamlit dashboard + results reader
src/        pipeline: grid, ingest/, features, scoring, constraints, model, pairing, explain, validate, results
tests/      pytest suite (make test)
results/    committed outputs of the last run (what the dashboard shows)
scripts/    download_data.py (parallel, resumable NASA downloads)
docs/       DATA.md (sources), VALIDATION.md (results + misses), TESTING.md, tasks/
config.yaml every threshold, weight and path, in one place
```

## Credits

See [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) and [AI_USAGE.md](AI_USAGE.md).
