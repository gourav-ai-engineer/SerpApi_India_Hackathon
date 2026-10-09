# Hackathon Submission Draft — CareerPilot AI

## Suggested project title

CareerPilot AI — Evidence-Driven Job Intelligence Agent

## Suggested short description

CareerPilot is a tool-using job research agent for early-career engineers. It uses SerpApi Google Jobs to discover structured vacancies, expands searches around a candidate's role and skills, removes duplicates, scores role fit transparently, and uses SerpApi Google Search to find employer-careers evidence. A local application tracker and CSV export turn search results into next actions. It labels uncertainty honestly: indexed search results do not prove a vacancy remains open.

## Recommended track

AI Agents.

## Explain the meaningful SerpApi integration

CareerPilot's primary workflow depends on two SerpApi engines. Google Jobs supplies the current structured job result payload used for normalization, deduplication, ranking, and shortlisting. Google Search then investigates the top-ranked roles for employer-careers pages or related evidence. The app records the supporting source and uses conservative labels when evidence is weak. SerpApi is core to both discovering jobs and building the evidence layer; it is not an isolated decorative call.

## Technical highlights

- Bounded query planning with an optional Gemini-driven planner and deterministic fallback.
- Validated model-generated search queries with strict query-count and length limits.
- Cross-query duplicate merging while preserving distinct application options.
- Explainable fit scores with component breakdowns and skill evidence.
- Independent search cross-checks with provenance and uncertainty labels.
- Local SQLite tracking, status lifecycle, shortlist CSV export, offline tests, and clear error handling.
- Synthetic data is visibly separated from live search results.

## AI tooling disclosure draft

ChatGPT was used as a coding assistant to help draft the initial implementation, documentation, and tests. The participant reviewed, ran, and remains responsible for the submitted code and claims. Add any other AI tools used during development before submission.

## Recording link

Replace this line with the public or unlisted demo video URL after recording. Verify the link in a private/incognito browser window.

## Final checks

- [ ] Public GitHub repository is accessible without sign-in.
- [ ] Application starts from the documented commands.
- [ ] Live SerpApi discovery works with a valid key.
- [ ] Demo video is under three minutes and shows live functionality.
- [ ] Video and README contain no secrets or API keys.
- [ ] AI tools are disclosed accurately.
- [ ] Project history/prior-work question is answered truthfully.
- [ ] Track, contact details, required forms, and terms acceptance are complete.
- [ ] Click the final Submit project action before the official deadline; a saved draft is not a submission.
