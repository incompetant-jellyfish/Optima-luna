# Lunar South Pole Site Suitability Ranker

> Instructions for Claude Code. Read this whole file before writing code. Follow the phases in order. Do not skip acceptance checks.

## 1. Goal

Build a hackathon-ready decision-support tool that divides the lunar south polar region (80°S–90°S) into grid cells, scores each cell for (a) landing safety and (b) resource/science value, and ranks candidate sites and landing/mining pairs. A small neural network generalizes a multi-criteria score across cells with missing data. Output is an interactive dashboard.

It is a decision-support tool, not a final site selector. Say so in the README and UI.

## 2. Hard rules

- Python 3.11+, managed with `uv` or `venv`. Pin dependencies in `requirements.txt`.

- **Never fabricate data silently.** If real data is missing, use the synthetic generator in `src/synth.py` and label every output and plot "SYNTHETIC" when it is used.

- Keep data out of git (`data/` in `.gitignore`). Keep configs and thresholds in `config.yaml`, not hard-coded.

- Every module gets a quick test or a runnable `__main__` demo. Run it before moving on.

- Commit after each phase with a clear message.

- Ask me before adding any paid service or heavy dependency (e.g. full GDAL builds).

## 3. Data sources (know the limits)

| Layer | Source | Use | Notes |

|---|---|---|---|

| DEM, slope, roughness | NASA LOLA (PDS) or Chandrayaan-2 TMC-2 DEM | landing safety | LOLA is the reliable baseline |

| Boulders / craters | Chandrayaan-2 OHRC (~0.25 m) | landing safety | Patchy coverage; treat as optional |

| Ice signature | Chandrayaan-2 DFSAR (CPR) | resource score | Partial coverage |

| Hydration | Chandrayaan-2 IIRS | resource score | Partial coverage |

| Temperature | LRO Diviner (PDS) | cold traps | Use as the thermal map |

| Thermal point validation | Chandrayaan-3 **ChaSTE** | single-point check near 69°S | NOT a map; use only as a sanity point |

| Illumination | LOLA-derived illumination maps | power potential | Fraction of time sunlit |

ISRO data comes from the ISSDC PRADAN portal (registration, downloads). There is no clean REST API. Write `src/ingest/pradan.py` as a loader that reads files from `data/raw/`, and document how to download them in `docs/DATA.md`. Do not scrape or bypass authentication. If files are absent, fall back to NASA PDS products or synthetic data.

## 4. Repo layout

```

.

├── idea.md

├── README.md

├── config.yaml

├── requirements.txt

├── docs/DATA.md

├── data/{raw,processed}/        # gitignored

├── src/

│   ├── ingest/                  # loaders per layer

│   ├── grid.py                  # polar stereographic grid, cell ids

│   ├── features.py              # per-cell feature extraction

│   ├── constraints.py           # hard landing masks

│   ├── scoring.py               # multi-criteria (AHP-style) scores

│   ├── model.py                 # MLP, training, inference

│   ├── explain.py               # feature attribution

│   ├── pairing.py               # landing/mining pair ranking

│   └── synth.py                 # synthetic data generator

├── app/                         # dashboard (Streamlit)

├── notebooks/

└── tests/

```

## 5. Phases and acceptance criteria

### Phase 0: Setup

Create the structure, `config.yaml`, and `requirements.txt` (numpy, pandas, rasterio, pyproj, scipy, scikit-learn, torch, shap, streamlit, plotly, pyyaml, pytest).

**Accept:** `pytest` runs; `python -m src.synth` produces a synthetic 80–90°S feature stack.

### Phase 1: Grid

Project to polar stereographic (south), build a regular grid of configurable cell size (default 1 km) covering 80°S–90°S. Each cell has an id, x/y, lat/lon.

**Accept:** cell count matches expected area within 2%; lat/lon round-trips correctly.

### Phase 2: Features

Per cell, compute: mean/max slope, roughness, boulder density, crater density, illumination fraction, permanent-shadow fraction, mean/min temperature, ice CPR index, hydration band depth, Earth line-of-sight fraction. Store a `data/processed/features.parquet` plus a `coverage` mask per feature (NaN means no data).

**Accept:** feature table loads; coverage report printed per layer.

### Phase 3: Constraints and scoring

- `constraints.py`: hard mask removing cells with slope above config threshold (default 10°), extreme roughness, or heavy boulder density. Thresholds live in config.

- `scoring.py`: two scores in [0,1] using weighted normalized features, weights from config:

  - landing safety (slope, roughness, boulders, illumination, comms)

  - resource/science value (ice, hydration, cold traps, terrain diversity)

- Handle missing features by reweighting over available ones and recording a per-cell `confidence` (share of weight with real data).

**Accept:** unit tests for monotonicity (steeper slope never raises landing score) and for missing-data reweighting.

### Phase 4: Neural network

- Label problem: there is no ground truth. Train an MLP (2–3 hidden layers) on pseudo-labels from the Phase 3 scores, using random feature masking during training so it learns to predict with missing layers. Hold out spatial blocks for validation (not random cells).

- Also train a simple baseline (linear regression or gradient boosting) and report both.

- Output predicted landing and resource scores plus an uncertainty estimate (MC dropout or ensemble).

**Accept:** held-out spatial block R² reported; model beats or matches baseline under masked inputs; saved to `models/`.

### Phase 5: Validation and explainability

- Validate: check whether top-ranked cells overlap known candidates (Shackleton rim, Malapert massif, Chandrayaan-3 site, Artemis candidate regions). Put coordinates in `config.yaml` with sources noted; verify them before use, and flag any you cannot confirm.

- `explain.py`: per-site feature attribution.

**Accept:** a validation report in `docs/VALIDATION.md` with honest results, including failures.

### Phase 6: Pairing

For each high-scoring landing cell, find the best nearby resource cell within a configurable radius (default 10 km) using a slope-based traversal cost. Rank pairs by combined score.

**Accept:** top-10 pairs table with distance, route cost, both scores, confidence.

### Phase 7: Dashboard

Streamlit app with a polar heatmap (toggle landing / resource / combined), top-N ranked list, weight sliders that re-rank live, a site detail card (feature breakdown, confidence, attribution), and a visible banner when synthetic data is in use.

**Accept:** `streamlit run app/main.py` works end to end on synthetic data.

### Phase 8: Demo polish

README with architecture diagram, how to download real data, results, limitations, and a 2-minute demo script in `docs/DEMO.md`.

## 6. Working style

- Start with Phase 0 and show me the plan for each phase in a few lines before coding.

- After each phase, summarize what changed, what was tested, and what is uncertain.

- Prefer simple and readable over clever. This is a primitive neural net by design.

- If a requirement is ambiguous or a dataset is unavailable, stop and ask rather than guess.

## 7. Known risks to keep in mind

- Data access and preprocessing will dominate the time budget.

- Layers have different resolutions; document the resampling rule in `docs/DATA.md`.

- Pseudo-label training mostly reproduces the scoring function. Be transparent about this and emphasize generalization to missing data.
