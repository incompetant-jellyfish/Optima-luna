# P2 guide: for P2's AI assistant

> **For the AI assistant P2 is working with.** Read this first, then `docs/tasks/P2.md` (the
> human brief: its step 1 is **already done**), `rules.md`, `idea.md`, `config.yaml`.
> Repo: https://github.com/incompetant-jellyfish/Optima-luna · branch `main`
> Freeze **4:00 AM**, submit **6:45 AM, 22 Nov 2026**.

## Project in one paragraph

Lunar South Pole Site Suitability Ranker (ASTRA 2026 hackathon). The region 80–90°S is cut
into 290,364 cells of 1 km (south polar stereographic, sphere R = 1737.4 km). Each cell has
12 features (slope, illumination, temperature, ice signal …). A weighted rule gives a
landing score and a resource score (0–1). P2 trains models that learn those scores
(pseudo-labels, **not** ground truth), pairs safe landing cells with nearby ice cells, and
checks NASA reference sites. Decision support only, never "the best landing site".

## Who owns what

| Person | Owns | Don't edit without asking |
|---|---|---|
| P1 | `config.yaml`, `src/grid.py`, `src/scoring.py`, `src/constraints.py`, `src/features.py`, `src/ingest/` | the data contract (column names, weights) |
| **P2 (you)** | `src/model.py`, `src/pairing.py`, `src/explain.py`, `src/validate.py`, `src/synth.py`, their tests, `docs/VALIDATION.md`, `results/` | |
| P3 | `app/`, README story sections, deck, video | |

## Current state (01:10 AM)

- P2's code lives in `src/` and `tests/`. The old overlay zip and nested folder are deleted:
  **never recreate them**, and pull before editing.
- `make test`: 48 passed, 1 skipped. Keep it green.
- `features.parquet` is currently **v1-lola**: illumination and PSR are real, the rest is
  SYNTHETIC. Real slopes arrive soon (the LOLA DEM is downloading). P1 sends the file; it is
  git-ignored, so it comes by Drive or USB to `data/processed/features.parquet`.
- `make model` works: ~40 s on CPU, ~0.7 GB RAM. sklearn `MLPRegressor` is CPU-only; the GPU
  is not used and does not need to be. **Do not port to PyTorch.**
- `results/` does not exist yet. P3's dashboard reader (`app/results_io.py`) expects it.

## Commands

```bash
make setup          # .venv + pinned requirements
make test           # all tests
make features       # P1: build features.parquet (has features_version column)
make model          # -> data/processed/scored_features.parquet, models/*.joblib, models/metrics.json
make pairs          # -> data/processed/pairs.parquet
make validate       # -> results/validation.csv
```

No `make` (Windows)? Use `.venv\Scripts\python -m src.model` etc.; the Makefile targets
are just `python -m src.<module>`.

**Never use `make synth` to produce results.** It writes `features.parquet` without a
`features_version` column. `make features` does the same synthetic fill *and* records the
version.

## Tasks, in order

### 1. Make pairing fast (blocker: currently 9+ minutes, never finished)

`rank_pairs` in `src/pairing.py` loops over **every** cell (290k) in Python and does pandas
work for ~300 neighbours each. Output is only the top `top_n` (10) pairs. Fix:

1. Only pair **eligible** landing cells: if the frame has `eligible`, filter
   `frame.eligible.fillna(False)`; otherwise compute it with
   `from src.constraints import landing_mask`.
2. Then keep only the best few thousand by landing score
   (e.g. `land.nlargest(max(2000, 50 * limit), landing_score)`). A cell outside that set
   cannot reach the top 10 by `combined_score`, since route cost only lowers the score.
3. Inside the loop, use numpy arrays (`resource[["x","y",...]].to_numpy()` once, then index)
   instead of `.iloc[...].copy()` + pandas columns per site.

Target: under 10 s on the full grid. Add a test that `rank_pairs` never returns an
ineligible landing cell. Keep the output columns exactly:
`landing_cell_id, ice_cell_id, distance_km, route_cost, landing_score, resource_score,
confidence, combined_score`.

### 2. One scoring definition

`model.py` has its own `_weighted_score` (line ~27) used by `make_pseudo_labels`. Replace it
with P1's:

```python
from src.scoring import score
scored = score(features)   # cell_id, landing_score, resource_score, landing_confidence,
                           # resource_confidence, confidence, eligible
```

Pseudo-labels = `scored.landing_score` / `scored.resource_score`; carry the confidences and
`eligible` through to the predictions. Delete `_weighted_score`. Adjust `tests/test_model.py`
if it called it directly. Never change weights or normalisation in `model.py`: those live in
`config.yaml` / `src/scoring.py` (P1).

### 3. Write `results/` (committed to git, so the demo and judges see it)

After model / pairs / validate, write a slim copy:

| File | Content |
|---|---|
| `results/predictions.parquet` | `cell_id, landing_score, resource_score, landing_uncertainty, resource_uncertainty, confidence` as float32, plus `features_version` |
| `results/pairs.parquet` | pairing output, columns as above |
| `results/metrics.json` | `models/metrics.json` + `"features_version"` + `"train_seconds"` |
| `results/validation.csv` | already written there by `make validate` |

`features_version` comes from the input `features.parquet` (column of the same name). Each
file < 20 MB. Scores stay 0–1 (P3 multiplies by 100). `.gitignore` ignores `data/` and
`models/`, **not** `results/`.

### 4. Retrain when P1 sends new features

Put the file at `data/processed/features.parquet`, then `make model pairs validate`, write
`results/`, commit. Send P3: held-out R² for landing / resource, MLP vs Ridge, clean vs
masked; training time; the rank and top-K status of Shackleton rim and Malapert massif.

### 5. `docs/VALIDATION.md`

State the features version, top-K, each reference site's rank, and for every miss which
feature pulled it down (use `src/explain.py`). Misses are reported, never hidden.

## Known data facts (don't be surprised)

- With synthetic slopes (max 8.65°) **100% of cells pass** the 10° slope limit. With real
  LOLA slopes this drops. Don't "fix" it in synth unless P1 agrees.
- Real illumination check: Shackleton floor = 0.00 sunlit / 1.00 PSR; Shackleton rim R04 0.21;
  Malapert R23 0.36. If your numbers disagree, the input file is stale.
- `earth_los_frac`, `crater_density`, `ice_cpr`, `hydration_depth`, `boulder_density` may stay
  SYNTHETIC; `<feature>_cov = False` marks that. The model already drops `_cov` and metadata
  columns from its inputs.

## Rules that bind you

- Honest metrics: R² measures how well the model imitates the scoring rule on held-out
  spatial blocks. It is **not** landing accuracy. Say so wherever a number is shown.
- Anything from synthetic data is labelled SYNTHETIC; never present v0 results as real.
- Log your AI use: add a row to `AI_USAGE.md` (tool, what it did, what a human checked).
- Credit libraries / data in `ACKNOWLEDGEMENTS.md`.
- Commit small, `git pull --rebase` before pushing, `make test` before every push. Never
  commit `data/`, `models/`, zips or nested copies of the repo.
- After 4:00 AM: retrain only for a real bug, and tell the team first.
