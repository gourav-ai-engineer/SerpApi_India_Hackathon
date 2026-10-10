# CareerPilot AI — Technical Design

## System boundaries

CareerPilot is a local-first research assistant. SerpApi is the source of live discovery/search results; the fit score and evidence classification are local heuristics. An optional Gemini call may propose search queries, but cannot create job records or assign evidence labels.

## Entry points

Both entry points drive the same `CareerPilotAgent.run()` pipeline in careerpilot.py; neither has its own search or ranking logic.

| | Streamlit UI (app.py) | CLI (`python careerpilot.py`) |
| --- | --- | --- |
| Profile input | Form fields, optional resume paste (skills detected locally) | `role` argument plus `--location`, `--skills`, `--work-mode`, `--experience` |
| Budget controls | Sidebar sliders | `--depth`, `--pages`, `--verify` |
| API keys | Sidebar field, or `.env` used server-side | Environment or `.env` only (`SERPAPI_API_KEY`, optional `GEMINI_API_KEY` / `GEMINI_MODEL`) |
| Output | Job cards, insights, trace, CSV export | Trace, top 15 ranked jobs, skill gaps; or the full run dict as JSON with `--json` |
| Persistence | SQLite tracker | None; the CLI never reads or writes the tracker |

The CLI exits with an argument error if no SerpApi key is set. Because the response cache lives in process memory, each CLI invocation starts with an empty cache and does not share cached results with a running UI.

## Request flow

1. The user enters role, location, skills, work preference, and experience in the UI or as CLI arguments.
2. The query planner produces at most three targeted variants. It uses Gemini when configured, otherwise a deterministic template. Model-generated queries must contain a role token, be at most 140 characters, contain no URL, and be unique.
3. The SerpApi client calls Google Jobs for each query, optionally following `serpapi_pagination.next_page_token` for up to three pages per query (stopping early when a page is empty or has no token). Request limits, errors, cache reuse, and returned result counts are visible in the trace.
4. A normalizer converts search results into a consistent schema. The deduplicator groups records by normalized employer, title, and location, merging application options instead of blindly duplicating cards.
5. The ranker calculates independent score components and stores the breakdown on each result.
6. Up to eight top-ranked jobs are cross-checked through SerpApi Google Search. Domain and career-page text are signals, not authoritative validation; labels preserve that uncertainty.
7. Market insights are aggregated from the ranked result set (see below).
8. Results are displayed with source provenance and can be exported as CSV or saved to SQLite (UI), or printed as text or JSON (CLI).

## SerpApi response cache

SerpApiClient keeps an in-memory cache of successful responses for 15 minutes, capped at 256 entries (oldest evicted first). The cache key is the sorted request parameters plus a truncated SHA-256 of the API key, so different keys never share results and the raw key is never part of the cache key. Cache hits are counted separately from billable `api_calls` in the run result and the UI. Failed requests are not cached. The cache is per process and is lost on restart.

## Market insights and resume skills

Both use a fixed, curated SKILL_VOCABULARY in careerpilot.py, so the analysis is deterministic, offline, and cannot be steered by search-result text.

- `market_insights(jobs, profile)` counts how many listings mention each vocabulary skill, then reports the top skills with their share of listings, skill gaps (top skills absent from the profile, up to five), top hiring companies, the share of listings mentioning remote work, showing a salary, or posted within about a week, and the average fit score. Shares describe only the current result set, not the wider market.
- `extract_skills_from_text(text)` matches pasted resume text against the same vocabulary. Short skills (three characters or fewer, such as Go or SQL) require word boundaries. Resume text stays in the Streamlit session; it is not sent to SerpApi or Gemini and not stored.

## Normalized job fields

- Identity: job_id, title, company, location
- Listing content: description, posted_at, schedule_type, salary
- Links: apply_options, apply_url, share_url
- Matching: score, score_breakdown, matched_skills, missing_skills, fit_reasons
- Evidence: verification_status, evidence_label, evidence_url, evidence_snippet
- Safety: is_demo

apply_url is populated only from a structured application option. Google's own results-page URL stays in share_url; it is not mislabeled as the employer's application page.

## Ranking

The fit score is a weighted rule-based ranking intended to help users sort a shortlist. It is not trained on hiring outcomes, has no access to the candidate's full resume unless manually entered, and is not calibrated as a probability.

## Persistence

SQLite stores saved job JSON, a status field, and free-text notes (capped at 2,000 characters). Older databases without the notes column are migrated automatically on first connection. Each operation opens and closes its own connection, committing on success and rolling back on error. The tracker can be exported as CSV. The database is created at data/careerpilot.db by default. Set CAREERPILOT_DB to use another writable path. No login system or cloud storage is implemented.

## Untrusted-content handling

All SerpApi and Gemini output is third-party data. safety.py provides the rendering guards used by app.py:

- `escape_html` for anything placed inside `unsafe_allow_html` blocks (company, location).
- `escape_markdown` for titles, snippets, skills, reasons, warnings, and trace lines, so injected Markdown links, HTML, or LaTeX render as literal text.
- `safe_http_url` before any link button: only absolute http(s) URLs without whitespace or quote characters are opened.
- `csv_safe` on every exported cell, prefixing values that start with `=`, `+`, `-`, `@`, tab, or carriage return to block spreadsheet formula injection.
- `is_valid_model_name` before the Gemini model name is inserted into the request URL path.

API keys from `.env` are used server-side and never pre-filled into password widgets. Network errors are reported with generic messages so request details are not echoed.

## Failure behavior

- Missing SerpApi credentials: live searches are blocked with an explicit UI error; the CLI exits with an argument error.
- Search failure on one query: the run records a warning and continues with other query results.
- Gemini disabled or unavailable: use deterministic search planning.
- Verification failure: mark the result as requiring manual review; do not invent proof.
- Empty results: show an empty state, not fabricated live jobs.
