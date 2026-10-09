# CareerPilot AI — Technical Design

## System boundaries

CareerPilot is a local-first research assistant. SerpApi is the source of live discovery/search results; the fit score and evidence classification are local heuristics. An optional Gemini call may propose search queries, but cannot create job records or assign evidence labels.

## Request flow

1. The user enters role, location, skills, work preference, and experience.
2. The query planner produces at most three targeted variants. It uses Gemini when configured, otherwise a deterministic template. Model-generated queries must contain a role token, be at most 140 characters, contain no URL, and be unique.
3. The SerpApi client calls Google Jobs for each query. Request limits, errors, and returned result counts are visible in the trace.
4. A normalizer converts search results into a consistent schema. The deduplicator groups records by normalized employer, title, and location, merging application options instead of blindly duplicating cards.
5. The ranker calculates independent score components and stores the breakdown on each result.
6. Up to eight top-ranked jobs are cross-checked through SerpApi Google Search. Domain and career-page text are signals, not authoritative validation; labels preserve that uncertainty.
7. Results are displayed with source provenance and can be exported as CSV or saved to SQLite.

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

SQLite stores saved job JSON and a status field. The database is created at data/careerpilot.db by default. Set CAREERPILOT_DB to use another writable path. No login system or cloud storage is implemented.

## Failure behavior

- Missing SerpApi credentials: live searches are blocked with an explicit UI error.
- Search failure on one query: the run records a warning and continues with other query results.
- Gemini disabled or unavailable: use deterministic search planning.
- Verification failure: mark the result as requiring manual review; do not invent proof.
- Empty results: show an empty state, not fabricated live jobs.
