# AI Usage Log

Official policy from the 21 Nov briefing: see `rules.md` §4 (TODO: paste once announced).

| When | Tool | What was generated | What the team changed / reviewed |
|---|---|---|---|
| 21 Nov 2026, evening | Claude Code (Claude Opus 5.5) | Draft pitch deck (14 slides) from `idea.md` and `rules.md`: slide text, layout, speaker notes. Results, status and validation slides left as `[placeholders]`, with no numbers invented. | TODO: team to review, fill placeholders with real results, edit wording |
| 21 Nov 2026, evening | Claude Code (Claude Opus 5.5) | Cut the pitch deck down to 6 denser slides to match the updated `rules.md` §6 (PPT in 6 slides). Placeholders kept; no results invented. | TODO: team to review and fill placeholders |
| 21 Nov 2026, evening | Claude Code (Claude Opus 5.5) | Applied team review to deck slides 2, 4, 5, 6: rewrote data/coverage/scope points, checked data sources against NASA and ISRO pages, replaced status slide with build plan and success checks, reworded impact slide. | Review requested by the team; TODO: team to check the rewrites |
| 21 Nov 2026, evening | Claude Code (Claude Opus 5.5) | Replaced deck slide 5 (build plan) with a features slide, as the team asked. | TODO: team to check the features match what gets built |
| 21 Nov 2026, evening | Claude Code (Claude Opus 5.5) | P1 Phase 0–1: repo scaffold (Makefile, config.yaml with the shared data contract, pinned requirements, .gitignore), `src/config.py`, `src/grid.py` (polar stereographic 1 km grid) and `tests/test_grid.py`, plus stubs for README, docs/DATA.md, ACKNOWLEDGEMENTS.md. Tests run and pass (7/7). | TODO (P1): read grid.py and be able to explain it |
| 21 Nov 2026, late evening | OpenAI ChatGPT (GPT-6) | Drafted P2 synthetic feature generator, nearest-neighbour landing/resource pairing, spatial-block pseudo-label model evaluation with layer masking, three-model ensemble spread, explanations, source-referenced validation utility, tests, and documentation updates. | The P2 implementation was tested in an isolated reconstructed copy of the repository; team must review and run after applying to the live working tree. No real dataset or scientific-performance result was generated. |
