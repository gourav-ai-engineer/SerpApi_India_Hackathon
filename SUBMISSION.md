# Hackathon Submission Draft — CareerPilot AI

## Suggested project title

CareerPilot AI — Evidence-Driven Job Intelligence Agent

## Suggested short description

CareerPilot is a tool-using job research agent for early-career engineers. It uses SerpApi Google Jobs to discover structured vacancies, expands searches around a candidate's role and skills, removes duplicates, scores role fit transparently, and uses SerpApi Google Search to find employer-careers evidence. A market-insights view turns the live result set into personal skill gaps ("Kubernetes appears in 40% of these listings and is missing from your profile"), and a local application tracker with notes and CSV export turns search results into next actions. The same agent also runs from the command line, printing a ranked shortlist or full JSON for scripting. It labels uncertainty honestly: indexed search results do not prove a vacancy remains open.

## Recommended track

AI Agents.

## Explain the meaningful SerpApi integration

CareerPilot's primary workflow depends on two SerpApi engines. Google Jobs supplies the current structured job result payload (following `next_page_token` for additional pages) used for normalization, deduplication, ranking, shortlisting, and market-demand analysis. Google Search then investigates the top-ranked roles for employer-careers pages or related evidence. The app records the supporting source and uses conservative labels when evidence is weak. SerpApi is core to both discovering jobs and building the evidence layer; it is not an isolated decorative call.

## Technical highlights

- Bounded query planning with an optional Gemini-driven planner and deterministic fallback.
- Validated model-generated search queries with strict query-count and length limits.
- Cross-query duplicate merging while preserving distinct application options.
- Explainable fit scores with component breakdowns and skill evidence.
- Independent search cross-checks with provenance and uncertainty labels.
- Market insights computed from live listings: most-requested skills, personal skill gaps, top hiring companies, and remote/salary/freshness shares.
- Resume skill detection that runs locally against a fixed vocabulary; resume text is never sent to an API.
- SerpApi pagination plus a 15-minute per-key response cache that saves search credits; cached and billable calls are reported separately.
- Headless CLI (`python careerpilot.py "AI Engineer" --skills "Python, RAG"`) that drives the same agent pipeline as the UI, with flags for location, work mode, experience, query depth, pages, and cross-checks. It prints the trace, ranked jobs with evidence status, and skill gaps, or the full run as JSON with `--json` for cron jobs and other tools. A run makes at most depth × pages + verify SerpApi requests.
- Conservative evidence matching: short company words must match a whole hostname label, so names like "X" cannot claim an unrelated site as the employer's careers page.
- Honest failure reporting: an invalid key or exhausted quota produces a clear error, never a green "complete" banner over an empty result.
- Security hardening: all search-result text is escaped before rendering (no XSS or injected links), only http(s) links are opened, CSV exports block spreadsheet formulas, `.env` keys are never exposed in UI fields, and the model name is validated before use in a URL.
- Local SQLite tracking with status lifecycle and notes, shortlist and tracker CSV export, 20 offline tests in CI plus an end-to-end check of the full UI flow against simulated SerpApi responses, and clear error handling.
- Synthetic data is visibly separated from live search results.

## AI tooling disclosure draft

ChatGPT was used as a coding assistant to help draft the initial implementation, documentation, and tests. Claude Code was used to review the code for security vulnerabilities, implement the fixes, and add the market-insights, resume-skill, pagination, caching, tracker-notes, and CLI features with their tests. The participant reviewed, ran, and remains responsible for the submitted code and claims. Add any other AI tools used during development before submission.

## Recording link

Replace this line with the public or unlisted demo video URL after recording. Verify the link in a private/incognito browser window.

## Final checks

- [ ] Public GitHub repository is accessible without sign-in.
- [ ] Application starts from the documented commands.
- [ ] Live SerpApi discovery works with a valid key.
- [ ] Market insights tab shows skill gaps for a live run.
- [ ] CLI command from the README runs with a valid key and prints ranked jobs.
- [ ] Demo video is under three minutes and shows live functionality.
- [ ] Video and README contain no secrets or API keys.
- [ ] AI tools are disclosed accurately.
- [ ] Project history/prior-work question is answered truthfully.
- [ ] Track, contact details, required forms, and terms acceptance are complete.
- [ ] Click the final Submit project action before the official deadline; a saved draft is not a submission.
