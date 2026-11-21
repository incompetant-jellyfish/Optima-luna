# Final presentation script

Deck: https://claude.ai/artifact/DcTzME7BdhKnFpu2SZ4NiS (speaker notes hold this same text).
Target **≈ 11:35**, hard stop **12:00**. Speaker tags are suggestions: P1 = data/core, P2 = model, P3 = app/story.

Delivery cues: **(PAUSE)** = let the rhetorical question land, about 1 s. **(BEAT)** = tiny comic pause before the punchline. **(CLICK)** = advance the next card. **(SWITCH)** = go to the browser.

| # | Slide | Speaker · time |
|---|---|---|
| 1 | Lunar South Pole Site Ranker | P3 · 0:25 · start the clock |
| 2 | Why would anyone park at the south pole? | P3 · 0:55 |
| 3 | So just look at a map. Easy, right? | P1 · 0:50 |
| 4 | Two questions. 288,000 times. | P3 · 0:35 |
| 5 | Eight steps. Zero magic. | P1 · 1:05 |
| 6 | How much of this is actually real? | P1 · 0:55 |
| 7 | No answer key? No problem. (Kind of.) | P2 · 0:45 |
| 8 | LIVE DEMO | P3 drives, P1 narrates · 2:15 · SWITCH TO THE BROWSER. Have the app open and loaded beforehand. Backup: screen recording. |
| 9 | Did the fancy model win? | P2 · 0:40 |
| 10 | We checked against NASA. We missed. | P2 · 0:50 |
| 11 | Things we won’t pretend about | P1 · 1:00 |
| 12 | What happens with more than one night? | P2 · 0:50 |
| 13 | Decision support, not decisions. | P3 · 0:30 · total ≈ 11:35 |

Rehearse with a timer. If you are over 11:30 at slide 10, cut the six drawbacks to the top three (labels, coverage, resolution).

## 1. Lunar South Pole Site Ranker

[P3 · 0:25 · start the clock]

Quick question. (PAUSE) If you had to park a lander worth a couple of billion dollars on the Moon, where would you put it?

(BEAT) “Somewhere flat” — correct, gold star. Also somewhere sunny, for power. Also somewhere near water ice, so the astronauts can drink, breathe and make rocket fuel. And ideally all three within driving distance.

That is exactly what we built: a map of the lunar south pole that tells you where to land, where the ice is, and how sure it is about both.

We’re Team Optima Luna — I’m [Name], with [Name] and [Name] — and for the next eleven minutes we are going to over-explain the Moon to you. Sorry in advance. (BEAT) Not really.
## 2. Why would anyone park at the south pole?

[P3 · 0:55]

So — why would anyone park at the south pole? (PAUSE)

Fun fact: the Moon’s axis is tilted only about one and a half degrees. Earth is tilted twenty-three and a half — that’s why we get seasons. The Moon basically doesn’t, so near the poles the Sun just… sits on the horizon. Forever. (CLICK)

That does two wonderfully weird things at once. First: some crater floors have not seen sunlight in billions of years. These permanently shadowed regions are among the coldest places ever measured in the solar system — cold enough that water ice just sits there, untouched. (CLICK)

Second: some ridges and rims stick up high enough to catch that sideways sunlight almost all the time. Perfect for solar panels. (CLICK)

So you get “always sunny” and “never sunny, full of ice” a few kilometres apart. Which is why Artemis, Chandrayaan and LUPEX are all heading here. (BEAT) It is, honestly, the most contested parking lot off Earth.
## 3. So just look at a map. Easy, right?

[P1 · 0:50]

So — just look at a map and pick a spot. Easy, right? (PAUSE) (BEAT) It was not easy.

The data absolutely exists. NASA and ISRO have mapped this region in ridiculous detail. The problem is the data does not want to be friends with itself.

One: it’s scattered — NASA’s geodesy archive, the Planetary Data System, ISRO’s PRADAN portal. (CLICK)

Two: it’s mismatched — different instruments flatten the round Moon into different map projections, at resolutions from 25 centimetres a pixel to hundreds of metres a pixel. (CLICK)

Three: it’s patchy — gaps, missing layers, and registration walls before you can download a single file. (CLICK)

So nobody hands you one map that says “land here, the ice is over there, and here’s why.” (BEAT) That’s the gap we went after.
## 4. Two questions. 288,000 times.

[P3 · 0:35]

So here’s our problem statement, and it’s just two questions. (CLICK)

Question A: can I land here without falling over? (CLICK)

Question B: is there ice worth driving to?

We ask both of those for every single square kilometre of the south pole — that’s about 288,000 times. Then we pair the good answers within 10 kilometres, which is a reasonable rover drive, and we put a confidence number on each one.

And — important — this is decision support. It narrows the search for humans. It does not pick a landing site and it is not mission-certified. (BEAT) Please don’t land anything based on our hackathon project. Yet.
## 5. Eight steps. Zero magic.

[P1 · 1:05]

How does it work? Eight steps, zero magic. (CLICK through the steps)

One — Grid. We cut 80 degrees south to the pole into 290,364 one-kilometre cells. That’s about 288,000 square kilometres — bigger than the UK. (BEAT) Yes, we checked. And it’s in polar stereographic, the same projection NASA uses, so their maps drop straight in with no warping.

Two — Ingest. NASA’s LOLA laser altimeter fired billions of laser pulses at the Moon. Its 40-metre elevation map is 15,200 by 15,200 pixels — 231 million heights. We read it in windows, never all at once, and it takes 13 seconds. Every cell gets 625 of those pixels, which gives us its mean slope, max slope and roughness, plus sunlight and permanent shadow from the illumination map.

Three — Features: twelve per cell, each flagged real or placeholder.

Four — Rules: slope over 10 degrees? Too rough? You don’t land there, no matter how pretty it is.

Five — Scores: weighted averages, every weight a live slider.

Six — a Model that copes with missing data. Seven — Pairs within 10 km. Eight — Check against NASA. (BEAT) And 48 automated tests making sure we didn’t lie to ourselves.
## 6. How much of this is actually real?

[P1 · 0:55]

So how much of this is actually real? (PAUSE) Great question. We asked it too.

Five of our twelve features are real NASA LOLA data: mean slope, max slope, roughness, sunlight and permanent shadow. That’s 42 percent of all the values. (CLICK)

The other seven — ice radar, hydration, temperature, boulders, craters, Earth visibility — are synthetic placeholders for now. And every single one is labelled. The app tells you this at the top of the screen, every time. A map that pretends to know things it doesn’t is worse than no map.

Two fun stories. NASA’s server gives you about 15 kilobytes a second, so the download was estimated at 45 hours. (BEAT) We wrote a downloader that grabs eight chunks at once — done in an hour and fifteen. And the sunlight file stores numbers with a hidden scale factor; for a while we thought it was percentages. It wasn’t. Now there’s a test for it.

Sanity check: our slopes put Shackleton’s floor at 3.6 degrees and its walls at about 30 — matching published values.
## 7. No answer key? No problem. (Kind of.)

[P2 · 0:45]

Okay, here’s a subtle one. How do you train a model when there’s no answer key? (PAUSE) Nobody has a list saying “this cell is a 73 out of 100.”

So we don’t pretend. Our model learns our scoring rule — and its real job is to keep ranking well when data goes missing, because real maps have gaps. (CLICK)

It’s a small neural network, three copies trained separately, so when they disagree you see a plus-or-minus spread. (CLICK) During training we randomly hide 15 percent of the inputs to make it tough. (CLICK) We test it on whole 10-kilometre blocks it has never seen, so it can’t just memorise neighbours. (CLICK) And we race it against Ridge regression, a plain linear baseline — because you should always check whether the fancy thing beats the simple thing.

Training takes 37 seconds on a laptop CPU.
## 8. LIVE DEMO

[P3 drives, P1 narrates · 2:15 · SWITCH TO THE BROWSER. Have the app open and loaded beforehand. Backup: screen recording.]

“Enough slides. Let’s go to the Moon.” (SWITCH)

1 · MAP (0:25) — “This is the whole south pole, from above. The pole is right in the middle; the dotted rings are latitude, the spokes are longitude — same projection as NASA’s own maps. Bright yellow is good, dark purple is bad. Those black speckles? Crater walls our safety rules threw out — and honestly, they trace the craters beautifully.” Hover a pixel: “Every pixel tells you its latitude, longitude and all three scores.”

2 · WEIGHTS (0:30) — Open Feature weights, drag slope_mean to 0. “What if your lander doesn’t care about slope? (BEAT) Brave. But watch — the whole map re-ranks instantly. Nothing is pre-baked.” Click Reset weights.

3 · SITE CARD (0:30) — Pick site #1. “Our current number one: landing 92, resource 80. The model says 85 plus-or-minus 5. Confidence: Medium — half the weight rests on real data. And this bar chart shows exactly why it scores what it scores.”

4 · NASA SITES (0:20) — Hover the Shackleton diamond. “These lilac diamonds are NASA’s own candidate sites — with our rank for each. Spoiler: it’s not great. We’ll explain.”

5 · PAIRS (0:20) — Scroll down. “Land here, drive there for ice: best ice cell within 10 km of each landing site.”

6 · MODEL (0:10) — Open About the model. “And the model’s scores, caveat printed right next to them.”

SWITCH BACK TO SLIDES.
## 9. Did the fancy model win?

[P2 · 0:40]

So — did the fancy neural network win? (PAUSE) (BEAT) Half of it did.

For landing, Ridge — the simple linear baseline — wins: 0.994 versus 0.969. Which makes sense, because our landing rule is basically linear. Ouch, but fair.

For resource, the neural network wins: 0.987 versus 0.965, and with 15 percent of inputs hidden it holds 0.558 against Ridge’s 0.425 — exactly the missing-data case we built it for.

And because we like saying the uncomfortable part out loud: R-squared here means “how well it copies our rule,” not “how good it is at picking landing sites.” The app prints that caveat right next to the numbers.
## 10. We checked against NASA. We missed.

[P2 · 0:50]

So did we match NASA’s chosen sites? (PAUSE) No. (BEAT) And we think that’s the most useful slide in this deck.

First, the sanity checks pass: Shackleton’s floor comes out zero percent sunlit, fully shadowed, 3.6 degrees — just like the literature. (CLICK)

Shackleton rim, NASA site R04: we rank it 281,536th. Why? NASA’s point sits on a narrow rim — but our one-kilometre cell around it also swallows the 30-degree crater wall. So the cell fails our slope rule. The rim is fine; our cell is too chunky to see just the rim. (CLICK)

Malapert, R23: rank 98,656. It passes every safety rule; it just doesn’t make the top ten on our current weights.

We could have quietly tuned the weights until NASA’s sites floated to the top. We didn’t. A tool that tells you why it disagrees with NASA is more trustworthy than one that only shows nice numbers. (BEAT) Reported, not tuned away.
## 11. Things we won’t pretend about

[P1 · 1:00]

So, the things we are not going to pretend about. (CLICK through)

Labels: there’s no ground truth, so the model learns our rule. It’s a rule-imitator, not an oracle.

Coverage: seven of twelve layers are still placeholders — including the ice radar, which is, slightly awkwardly, the most important one for finding ice. (BEAT)

Resolution: one-kilometre cells blur narrow crater rims — that’s the Shackleton miss you just saw.

Hazards: a 40-metre elevation map cannot see a boulder the size of a car. Your lander can.

Routes: our route cost is distance times slope, not a real path planner that drives around craters.

Uncertainty: the plus-or-minus is the ensemble disagreeing with itself, not a calibrated error bar.

Every single one of these is written in our README and our validation report — and every one has a fix on the next slide.
## 12. What happens with more than one night?

[P2 · 0:50]

So what happens with more than one night? (PAUSE)

In weeks: real resource data. Chandrayaan-2’s DFSAR radar for ice, its IIRS spectrometer for hydration — both through ISRO’s PRADAN portal — plus Diviner temperatures. Each one replaces a placeholder; nothing else changes, and confidence goes up on its own. (CLICK)

In months: sharper ground. The 20-metre elevation map and 250-metre cells along crater rims — that fixes the Shackleton miss. Chandrayaan-2’s OHRC camera at 25 centimetres a pixel — you can literally see individual rocks — for boulder maps. And a real slope-aware path planner. (CLICK)

Later: real labels. If mission experts rate a set of sites, the model finally learns from humans instead of from our rule — and stops being an imitator.

The design point we’re proudest of: every upgrade is a data swap in one config file. (BEAT) Not a rewrite.
## 13. Decision support, not decisions.

[P3 · 0:30 · total ≈ 11:35]

So — where should you park that billion-dollar lander? (PAUSE)

We can’t tell you exactly. (BEAT) But we can turn 288,000 square kilometres into a short list that explains itself: why each site ranks where it does, how much of that is real data, and — when it disagrees with NASA — why.

In one night: real LOLA terrain and sunlight, hard safety rules, transparent scores, a model built for missing data, and landing-to-ice pairs. Every number traceable, every gap labelled.

Decision support, not decisions. The app is live at the link on screen, the code and the validation report are on GitHub. Thank you — questions?

[Likely questions, one line each: Why 1 km? — balance of DEM resolution, compute and the 10 km pairing; rims need finer, it’s on the roadmap. Why not deep learning on images? — no labels; a transparent rule plus a model that survives gaps was the honest choice. How do you know slopes are right? — Shackleton floor 3.6°, walls 30°, matching published values. What would change your top 10 most? — real ice radar from Chandrayaan-2 DFSAR.]
