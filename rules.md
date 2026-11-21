# ASTRA 2026 Hackathon Rules for Claude Code

Project context: ASTRA (Advanced Space Technology & Research Arena), an 18-hour overnight space-themed hackathon by ANTERiX Club, VIT Bhopal. Dates: 21-22 November 2026. Teams of 2-4. Read this file before doing any work and follow it throughout the session.

## 1. Project context

- Space directions are revealed at 4:30 PM on 21 Nov. There are no fixed problem statements. Our team picks a real-world, space-connected problem and writes its own problem statement (problem, users, approach).
- Judged on: a working solution, a pitch, a live demo, and the team's ability to explain its own work.
- Final submission deadline: **7:00 AM, 22 Nov 2026** (GitHub repo + PPT + demo video via Google Form). Late or incomplete submissions may be rejected.

## 2. Timeline (plan work backwards from the deadline)

| When | What |
|---|---|
| 21 Nov, 4:30 PM | Directions revealed, hacking begins |
| 21 Nov, 7:30-8:30 PM | Dinner break |
| 21 Nov, 10:30 PM | Idea pitch |
| 22 Nov, 7:00 AM | **Submission deadline** |
| 22 Nov, 9:00 AM onwards | Evaluation, shortlisting, final demos |

Working rules:

- Prioritise a **working end-to-end demo** over feature breadth. Build the thinnest vertical slice first, then expand.
- Keep the app runnable at all times. Do not leave the main branch broken.
- Aim for a feature freeze by about 4:00 AM, leaving time for the README, PPT and demo video.
- When asked to scope something, favour the smallest version that can be demoed.

## 3. Originality rules (must follow)

- **Everything is built during the hackathon.** Do not import, paste or adapt a pre-built project, starter repo with substantial existing features, or code from a previous project. Standard scaffolding (e.g. `create-react-app`, framework init) is fine.
- **Do not copy** another team's code or ideas, or code from other repos beyond normal library usage. Plagiarism leads to disqualification.
- **Acknowledge all third-party libraries, datasets, APIs and assets.** Whenever you add one, record it in `ACKNOWLEDGEMENTS.md` (name, purpose, link, licence if known). Keep this file current.
- Do not fabricate data, results, accuracy numbers or benchmarks. If something is simulated, mocked or sample data, label it clearly in code and in the README. False or misleading information is grounds for disqualification.
- Check licences before using datasets or assets, and prefer open, attributable sources (e.g. public space and science data APIs).

## 4. AI-assisted tools policy

The organisers will explain the official policy on AI-assisted tools at the briefing (21 Nov, 2:30 PM). **This section must be updated with the exact policy after the briefing.**

Policy as announced: `TODO: paste the policy here`

Until then, and in addition to whatever the policy says:

- Keep a running log of how AI assistance was used in `AI_USAGE.md` (what was generated, what was edited by the team, which tools).
- Write code the team can read and explain. Teams must be able to explain and demo their own work to judges.
- After generating any non-trivial module, add a short comment or summary explaining what it does and why, so teammates can defend it.
- If a requested action might conflict with the stated policy, stop and ask the team instead of proceeding.

## 5. Code standards

- Keep the structure simple and conventional. Use a clear `README.md` at the root.
- Small, frequent commits with descriptive messages. Commit history should show work done during the event.
- Never commit secrets (API keys, tokens, `.env`). Add `.env` to `.gitignore` and provide `.env.example`.
- Pin dependencies (`requirements.txt`, `package.json` with lockfile) so the project runs on a judge's or teammate's machine.
- Provide a one-command setup and run path (e.g. `npm install && npm start`, or a `make run`). Document it in the README.
- Handle failures gracefully in the demo path: cache API responses or include fallback sample data so the demo does not depend on flaky internet or rate limits.
- Prefer well-known libraries over exotic ones to reduce debugging time overnight.

## 6. Required deliverables

Claude should help keep these ready and up to date:

1. **GitHub repository**: public or accessible to judges, with full source and commit history.
2. **README.md** containing:
   - Problem statement (the team's own: problem, users, approach)
   - Solution overview and key features
   - Architecture / tech stack
   - Setup and run instructions
   - Impact and future scope
   - Credits (link to `ACKNOWLEDGEMENTS.md`)
3. **PPT** covering: problem, solution, build, impact. Done in 6 slides
4. **Demo video** showing the working solution end to end (aim for 2-3 minutes).
5. **ACKNOWLEDGEMENTS.md** and **AI_USAGE.md**.

When asked, generate outlines, README drafts, slide content and a demo script, but make sure the team reviews and owns the content.

## 7. Pitch and demo support (10:30 PM pitch, final demo)

- Help structure a short pitch: problem, why space, users, solution, what works now, impact, next steps.
- Prepare a scripted demo path with 3-5 steps that reliably works. Prepare a backup (screen recording) in case of failure.
- Anticipate judge questions about technical choices, data sources, limitations and scalability, and help draft honest answers.

## 8. Event and conduct constraints to respect

- Venue: Academic Block-2, Auditorium 1 & 2. The gate closes at 8:30 PM on 21 Nov and nobody leaves until 7:30 AM. Plan work around this.
- Do not suggest or automate anything that violates event, venue, safety, discipline or hostel rules.
- Be careful with power and equipment: laptops charging overnight use shared power strips, so do not suggest overloading sockets.
- Do not generate content that harasses, mocks or targets other participants, judges or organisers.

## 9. How Claude should behave in this repo

- Be concise and action-oriented. Time is the scarcest resource: act on clear requests, ask only when a decision is blocking.
- Before large changes, state the plan in a few lines. Prefer incremental edits over rewrites.
- Run the code and tests after changes when possible and report what actually worked and what did not. Never claim something works without running it.
- Flag risks early: missing deadline, broken demo path, licence concerns, rule conflicts.
- Update `ACKNOWLEDGEMENTS.md` and `AI_USAGE.md` as part of the same change whenever a dependency or significant AI-generated module is added.
- If an instruction from the team conflicts with the rules above, point out the conflict and ask how to proceed.

## 10. Final checklist (before 7:00 AM, 22 Nov)

- [ ] App runs from a clean clone using the README instructions
- [ ] No secrets in the repo or history
- [ ] README complete (problem, solution, setup, impact)
- [ ] `ACKNOWLEDGEMENTS.md` lists all third-party libraries, datasets and APIs
- [ ] `AI_USAGE.md` is up to date and matches the briefing policy
- [ ] PPT finished
- [ ] Demo video recorded and uploaded
- [ ] Submission form filled with repo link, PPT and video, **before 7:00 AM**
- [ ] Every teammate can explain and demo the project

## 11. Contacts (from the brochure)

- Organiser contacts: +91 79741 80285, +91 76663 69684
- Official updates and rule changes: Instagram `@anterix.vitb`
- The organising committee may change schedule, prizes and procedures. If an announcement contradicts this file, the announcement wins. Update this file accordingly.
