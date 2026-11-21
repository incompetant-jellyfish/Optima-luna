# Lunar South Pole Site Suitability Ranker

ASTRA 2026 hackathon project. A decision-support tool that divides 80°S–90°S on the Moon
into 1 km cells, scores each for landing safety and resource value, and pairs safe landing
cells with nearby ice. **It is decision support, not a final site selector.**

> Work in progress. Problem statement, features, architecture, results and impact: TODO (P3).

## Setup and run

```bash
make setup      # create .venv and install pinned requirements
make test       # run the tests
make grid       # build the 1 km polar grid and print a summary
make run        # start the dashboard (once app/main.py exists)
```

Requires Python 3.11+. On NixOS the Makefile adds the needed system libraries automatically.

## Data

See [docs/DATA.md](docs/DATA.md). Data is not in git.

## Credits

See [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) and [AI_USAGE.md](AI_USAGE.md).
