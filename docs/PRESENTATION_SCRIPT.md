# Final presentation script

Deck: https://claude.ai/artifact/DcTzME7BdhKnFpu2SZ4NiS (speaker notes hold this same text).
Target **≈ 11:20**, hard stop **12:00**. Speaker tags are suggestions: P1 = data/core, P2 = model, P3 = app/story.

| # | Slide | Speaker · time |
|---|---|---|
| 1 | Lunar South Pole Site Ranker | P3 · 0:20 · start the clock |
| 2 | The most contested ground off Earth | P3 · 0:50 |
| 3 | The data exists. It doesn’t fit together. | P1 · 0:50 |
| 4 | Two questions, every square kilometre | P3 · 0:35 |
| 5 | One grid. Every layer. One rule. | P1 · 1:05 |
| 6 | Real where we have it. Labelled where we don’t. | P1 · 0:50 |
| 7 | Built to survive missing data | P2 · 0:45 |
| 8 | LIVE DEMO | P3 drives, P1 narrates · 2:15 · SWITCH TO THE BROWSER. Have the app open and loaded beforehand. Backup: screen recording. |
| 9 | What the numbers say | P2 · 0:40 |
| 10 | We checked against NASA. We missed. | P2 · 0:50 |
| 11 | What this is not (yet) | P1 · 1:00 |
| 12 | Where it goes next | P2 · 0:50 |
| 13 | Decision support, not decisions. | P3 · 0:30 · total ≈ 11:20 |

Rehearse with a timer. If you are over 11:30 at slide 10, cut the six drawbacks to the top three (labels, coverage, resolution).

## 1. Lunar South Pole Site Ranker

[P3 · 0:20 · start the clock]

Good morning. We are Team Optima Luna. In the next ten minutes we’ll show you a tool that answers three questions about the Moon’s south pole: where is it safe to land, where is the ice, and — the part most tools skip — how sure are we about each answer.

It covers everything from 80 degrees south to the pole, cut into 290,364 one-kilometre cells, built on real NASA LOLA laser-altimeter data. Let’s start with why anyone cares about this patch of the Moon.
## 2. The most contested ground off Earth

[P3 · 0:50]

The lunar south pole is the most contested real estate off Earth, for two reasons that sit right next to each other.

First, water ice. The Moon’s spin axis is almost upright, so near the pole the Sun skims the horizon and the floors of deep craters never see it. Those permanently shadowed craters are cold traps, and they hold water ice — drinking water, oxygen, rocket fuel, made on the Moon instead of hauled from Earth.

Second, sunlight. A few kilometres away, crater rims and ridges stay lit for long stretches, which means solar power and milder temperatures.

That is why NASA’s Artemis, ISRO’s Chandrayaan programme and the ISRO–JAXA LUPEX mission all point here.

The catch: the ice is in the dark and the power is in the light. The best site is a trade-off between the two, a few kilometres apart. Finding that trade-off is the problem.
## 3. The data exists. It doesn’t fit together.

[P1 · 0:50]

The data to make this decision already exists. The problem is that it doesn’t fit together.

It’s scattered: terrain and sunlight from NASA’s LOLA laser altimeter sit on NASA’s Planetary Geodesy archive; temperatures from LRO’s Diviner sit on the Planetary Data System; ice radar and spectra from Chandrayaan-2 sit on ISRO’s PRADAN portal, behind registration.

It’s mismatched: different map projections, resolutions from 20 metres to hundreds of metres, raster images in one place and 600-megabyte text tables in another.

And it’s patchy: some layers have gaps, some aren’t downloadable in a night, and one NASA server we needed throttles every connection to about 15 kilobytes a second — our teammate’s first download estimate was 45 hours.

So comparing two candidate sites today means stitching all of this together by hand. We wanted one map where every layer lines up, every number is traceable to its source, and the gaps are shown, not hidden.
## 4. Two questions, every square kilometre

[P3 · 0:35]

So our problem statement is deliberately narrow. For every one-kilometre cell between 80 degrees south and the pole, answer two questions.

A: is it safe to land here — flat enough, smooth enough, sunlit enough?

B: is it worth going to — is there evidence of ice, cold enough to keep it?

Then pair the answers: for each good landing cell, find the best resource cell within ten kilometres of driving.

And for every answer, say how much of it rests on real measurements versus placeholders.

What it is not: it is decision support. It narrows 288,000 square kilometres to a short, explainable list. It is not a final site selector and it is not a mission-certified hazard assessment — and we’ll be explicit about where it falls short.
## 5. One grid. Every layer. One rule.

[P1 · 1:05]

Here is the whole system in eight steps.

One — Grid. We cut 80 degrees south to the pole into 290,364 one-kilometre cells, in the same polar stereographic projection NASA uses for its LOLA maps, so NASA’s rasters drop straight in with no reprojection.

Two — Ingest. We read the 40-metre LOLA elevation model in windows — 15,200 by 15,200 pixels, never loaded whole — and compute, for each cell, mean slope, maximum slope and roughness from 625 pixels. The illumination map gives each cell’s average sunlight and the fraction that is permanently shadowed. The whole DEM takes about 13 seconds.

Three — Features. Twelve per cell, each with a flag saying whether it is real data or a placeholder.

Four — Rules. Hard limits first: mean slope above 10 degrees, too rough or too bouldery, and the cell can’t be a landing site, whatever else it scores.

Five — Scores. Landing and resource scores are weighted averages of normalised features; the weights are in one config file and live sliders in the app.

Six — Model. A neural network ensemble learns those scores so it can still rank cells when a layer is missing.

Seven — Pairs: each good landing cell gets its best ice cell within 10 kilometres.

Eight — Check: we test the ranking against NASA-published sites. 48 automated tests keep it honest.
## 6. Real where we have it. Labelled where we don’t.

[P1 · 0:50]

Let me be precise about what is real.

Five of our twelve features come from real NASA data: mean slope, maximum slope and roughness from the 40-metre LOLA elevation model, and average sunlight and permanent shadow from LOLA’s illumination maps. That is 42 percent of all feature values.

The other seven — ice radar, hydration, temperature, boulders, craters, Earth visibility — are placeholders tonight, because the Chandrayaan-2 data needs ISSDC registration and the Diviner product is a 600-megabyte table we didn’t have time to grid properly.

Placeholders are never presented as data. Every value carries a flag, the app shows a “partly synthetic” banner, and every score comes with a confidence: the share of its weight that rests on real measurements. A site scored mostly from placeholders says “Low confidence”, in words, on screen.

One engineering note: NASA’s server throttles each connection to about 15 kilobytes a second. We wrote a parallel, resumable downloader that splits files into byte ranges — the 45-hour estimate came down to about an hour. Every file’s source URL is logged.
## 7. Built to survive missing data

[P2 · 0:45]

Why a model at all, if we already have a scoring rule? Because the rule breaks when a layer is missing, and at the pole layers are always missing somewhere.

So we train a small neural network — two hidden layers — to reproduce the score, and during training we randomly hide 15 percent of the input layers on every pass, so it learns to rank a cell even when, say, temperature isn’t there.

We train three of them; where they disagree, the app shows a plus-or-minus spread. It is a simple signal, not calibrated uncertainty, and we label it that way.

To test it fairly, we hold out whole 10-kilometre blocks of terrain, not random cells — neighbouring cells look alike, and random splits would flatter us.

And it has to beat a plain linear Ridge regression to earn its place. Training takes 37 seconds on a laptop CPU.

One honest caveat up front: there are no ground-truth labels for “good landing site”. The targets are our own rule. So the model’s accuracy means “reproduces the rule”, not “picks the right site”. You’ll see the app now, then the numbers.
## 8. LIVE DEMO

[P3 drives, P1 narrates · 2:15 · SWITCH TO THE BROWSER. Have the app open and loaded beforehand. Backup: screen recording.]

1 · MAP (0:20) — “This is the whole south polar region, 80 degrees to the pole. Each pixel is the combined score; bright is better. The dark speckles are cells that fail the hard landing rules — steep crater walls. The numbered squares are the top ten sites, at least 5 kilometres apart.”

2 · WEIGHTS (0:30) — Open Landing weights, drag slope_mean to 0. “Every weight is live. If a mission cares less about slope — say, a lander with better hazard avoidance — the ranking changes instantly. Nothing is hard-coded.” Click Reset weights.

3 · SITE CARD (0:30) — Pick site #1. “For any site: landing, resource and combined scores; the model’s prediction with its plus-or-minus spread; and confidence — here Medium, because half of the weight rests on real data. This bar chart shows exactly which feature contributed what. The table says, line by line, which values are real NASA data and which are synthetic.”

4 · NASA SITES (0:20) — Hover the Shackleton diamond. “These diamonds are NASA-published reference points: Shackleton rim and Malapert massif, with our rank for each. We’ll come back to why they rank where they do.”

5 · PAIRS (0:20) — Scroll to pairs. “For each top landing cell, the best resource cell within 10 kilometres: distance, a simple route cost, and a combined score.”

6 · MODEL (0:15) — Open About the model. “And the model’s numbers, with the caveat printed right there: R-squared is not landing accuracy.”

SWITCH BACK TO SLIDES.
## 9. What the numbers say

[P2 · 0:40]

The numbers, from whole 10-kilometre blocks the models never saw.

Landing: the simple Ridge baseline wins — 0.994 against the neural network’s 0.969, and it stays ahead when we hide 15 percent of the inputs. That makes sense: our landing rule is close to linear in slope and sunlight, so a linear model fits it almost perfectly. We report that rather than hide it.

Resource: the neural network wins — 0.987 against 0.965, and with inputs hidden 0.558 against 0.425. The resource score mixes ice, cold and shadow in a less linear way, and that is where the masking training pays off. The drop with hidden inputs also tells you how much the resource score depends on layers that are still placeholders.

And one physical result: with real LOLA slopes, 62 percent of cells pass the landing rules. With placeholder slopes, 100 percent passed — which is exactly why real data mattered.

Again: R-squared here measures how faithfully a model reproduces our rule. It does not measure landing safety.
## 10. We checked against NASA. We missed.

[P2 · 0:50]

We validated in two ways.

First, physical sanity. Shackleton crater’s floor comes out at zero percent sunlight, 100 percent permanent shadow and 3.6 degrees slope — a flat, dark cold trap, as it should be. Its inner walls come out at 30 degrees, matching their known 30-to-35-degree slopes. Malapert massif comes out at 7 degrees and 36 percent sunlight. The data pipeline is right.

Second, the hard test: two reference points from NASA’s Lunar Surface Data Book, Shackleton rim and Malapert massif. Both missed our top ten.

Shackleton rim ranks 281,536th. The reason is resolution: the rim is a narrow crest, and the nearest one-kilometre cell is mostly the 30-degree crater wall beside it, so it fails the slope rule. At 1 kilometre, we cannot separate a ridge-top from the cliff next to it.

Malapert ranks 98,656th: it passes every rule, but under our weights it is good, not exceptional. NASA weighs things we don’t model — communications, traverses, science.

We are reporting these misses, not tuning the weights until NASA’s sites float to the top. That would be fitting the answer.
## 11. What this is not (yet)

[P1 · 1:00]

Six drawbacks, in order of how much they matter.

One: labels. Nobody has labelled the Moon’s good landing sites, so our model learns our own scoring rule. It can be no better than the rule and the weights we chose.

Two: coverage. Seven of twelve layers are placeholders tonight, including the ones that matter most for resources — ice radar and temperature. The resource map is the least trustworthy part of the product, and the confidence score says so.

Three: resolution. One-kilometre cells average a narrow crater rim with the cliff beside it — that is exactly why Shackleton rim failed.

Four: hazards. A 40-metre elevation model cannot see boulders or small craters that can tip a lander; that needs Chandrayaan-2’s 25-centimetre OHRC camera.

Five: routes. Our route cost is straight-line distance times average slope. It does not plan a path around a cliff.

Six: uncertainty. The plus-or-minus is the spread of three models. It is a useful flag, but it is not a calibrated probability.

None of these is hidden in the product: each one is printed in the app, the README or the validation report.
## 12. Where it goes next

[P2 · 0:50]

The roadmap follows the drawbacks, and the architecture already has a slot for each step.

Next, in weeks: real resource data. Chandrayaan-2’s dual-frequency radar for ice signatures and its IIRS spectrometer for hydration, through ISRO’s PRADAN portal, plus Diviner temperatures. Each one replaces a placeholder layer; nothing else changes, and confidence rises automatically.

Then, in months: sharper ground. The 20-metre DEM and finer 250-metre cells along crater rims would fix the Shackleton miss. Chandrayaan-2’s OHRC camera, at 25 centimetres, would let us map boulders directly. And a real path planner — a least-cost route over the slope map — would replace our straight-line route cost.

Later: real labels. If mission experts rate a set of sites, the model can learn from them instead of from our rule — that is when it stops being a rule imitator and becomes a genuine predictor. Add calibrated uncertainty and Earth-communication windows, and it becomes a tool a mission team could actually plan with.

The key design point: every upgrade is a data swap in one config file, not a rewrite.
## 13. Decision support, not decisions.

[P3 · 0:30 · total ≈ 11:20]

To close. In one night we turned scattered NASA archives into one map of the lunar south pole: 290,364 cells, real LOLA terrain and sunlight, hard safety rules, transparent scores, a model built to survive missing data, and landing-to-ice pairs — every number traceable to its source and every gap labelled.

It narrows 288,000 square kilometres to a short list that explains itself: why each site ranks where it does, and how much of that rests on real data.

And when it disagrees with NASA, it says so, and says why.

Decision support, not decisions. The app is live at the link on screen, the code and the validation report are on GitHub. Thank you — we’re happy to take questions.

[Likely questions, one line each: Why 1 km? — balance of DEM resolution, compute and the 10 km pairing; rims need finer, it’s on the roadmap. Why not deep learning on images? — no labels; a transparent rule plus a model that survives gaps was the honest choice. How do you know slopes are right? — Shackleton floor 3.6°, walls 30°, matching published values. What would change your top 10 most? — real ice radar from Chandrayaan-2 DFSAR.]
