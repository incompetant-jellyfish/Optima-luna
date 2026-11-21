# Manual testing guide

Each check says what to do and what you should see. ~20 minutes for everything.

## 0. Automated tests (1 min)

```bash
make test
```
Expect: `48 passed, 1 skipped` (the skip is the synthetic-banner test, which only runs when
no real features file exists).

## 1. Fresh clone runs (5 min) — do this on the demo laptop

```bash
git clone https://github.com/incompetant-jellyfish/Optima-luna.git /tmp/ol && cd /tmp/ol
make setup && make run
```
Open the printed `Local URL`. Expect, with **no** `data/` folder:
- Yellow banner **PARTLY SYNTHETIC – 42% of feature values are real**.
- Red top-N markers and two **orange diamonds** (Shackleton rim, Malapert) on the map.
- Pairs caption says `Source: results/pairs.parquet`.

## 2. Dashboard (5 min)

| Do | Expect |
|---|---|
| Switch "Map shows" between Combined / Landing / Resource | Map and top-N list change |
| Open *Landing weights*, set `slope_mean` to 0 | Ranking changes instantly (< 1 s) |
| Click **Reset weights** | Back to the defaults |
| Untick "Hide cells failing hard landing constraints" | More cells coloured; steep crater walls appear |
| Pick a site in *Site detail* | Cyan ring moves to it on the map |
| Site card | Landing / Resource / Combined (0–100), **Model landing ± spread**, confidence (High/Medium/Low) and "Passes hard landing constraints" |
| Feature table on the card | slope, roughness, illumination, PSR say **real**; ice, temperature etc. say **SYNTHETIC / none** |
| Hover an orange diamond | "rank N, in top-10: no" |
| Open *About the model* | R² metrics; caption says R² is not landing accuracy |
| Pairs table | 10 pairs sorted by combined score, distance ≤ 10 km |

## 3. Science sanity checks (3 min)

```bash
make -s scores
```
Expect `Eligible for landing: 61.9% of cells`. Then in the app, find these with the map hover
or the numbers in `docs/VALIDATION.md`:

| Place | Expect | Why |
|---|---|---|
| Shackleton crater floor (89.67°S, 129.8°E) | illumination 0.00, PSR 1.00, slope ~4° | Permanently shadowed, flat floor |
| Shackleton inner wall | slope ~30° | Known 30–35° walls |
| Malapert massif R23 | slope ~7°, illumination ~0.36 | Gentle, often sunlit |

If these are off, the input files are stale: rerun `make ingest features`.

## 4. Full rebuild from raw data (optional, ~2 min after download)

```bash
python3 scripts/download_data.py --only illum dem
make ingest features scores train test
git status results/      # new results if anything changed
```
Expect: `Trained in ~40 s on features v1-lola`, `Wrote 10 pairs`, `Wrote results/: ...`.

## 5. Failure behaviour (2 min)

| Do | Expect |
|---|---|
| `mv results /tmp/r && mv data /tmp/d`, restart app | Red **SYNTHETIC DATA** banner, "Model results not found" note, SYNTHETIC placeholder pairs warning; no crash |
| Restore: `mv /tmp/r results && mv /tmp/d data` | Back to normal |

## 6. Deployed app

Open the live link from the README and repeat section 2. First load takes ~30 s while it
reads the data.
