# CareerPilot AI — Evidence-Driven Job Intelligence Agent

**Hackathon track:** AI Agents  
**Stack:** Python · Streamlit · SerpApi Google Jobs · SerpApi Google Search · SQLite

CareerPilot turns job search into a repeatable research workflow: discover roles, merge duplicate listings, rank fit against a candidate profile, look for employer-careers evidence, and track applications. Its differentiator is an explicit evidence layer: the app separates an employer application URL from Google's listing URL, shows why a role ranked highly, and labels uncertainty rather than pretending a vacancy is verified or still open.

> Search evidence is not proof that a job is still open or that an employer/recruiter is legitimate. Always inspect the destination before sharing personal information.

## Why SerpApi is core

CareerPilot uses two SerpApi engines in its primary workflow:

1. **Google Jobs (engine=google_jobs)** supplies structured live job results such as title, company, location, description, posting-age signal, salary when available, and application options. A bounded query plan searches the candidate's role and skills.
2. **Google Search (engine=google)** independently looks for employer-careers pages or related evidence for top-ranked results. Evidence labels and supporting URLs are retained in the shortlist.

Without Google Jobs, the shortlist cannot be created. Without Google Search, independent source-evidence labels cannot be produced. This is material integration, not a cosmetic API call. See the [Google Jobs API docs](https://serpapi.com/google-jobs-api) and [Google Search API docs](https://serpapi.com/search-api).

A Gemini model can optionally propose search queries. Its output is bounded and validated before use; when the model is not configured or unavailable, CareerPilot falls back to built-in query planning. The model never creates job records, application links, or evidence labels.

## Features

- Live, structured job discovery from SerpApi.
- Bounded query planning (one to three queries).
- Duplicate merging by employer, title, and location while preserving distinct application options.
- Explainable fit score: role-title alignment (35%), skill mentions (38%), location/work-mode fit (15%), seniority fit (7%), and posting-age signal (5%).
- Top-result cross-checks through Google Search with evidence labels and source links.
- Source integrity: a Google listing URL is not relabeled as an employer application URL.
- Local SQLite application tracker: Saved, Applied, Interview, Offer, Rejected.
- CSV export for live shortlists.
- Visible agent trace showing planning, requests, deduplication, evidence decisions, and warnings.
- Synthetic offline demo mode, clearly labelled and never presented as live vacancies.
- **Market insights tab:** most-requested skills across the live result set, your personal skill gaps, top hiring companies, and remote/salary/freshness shares.
- **Resume skill detection:** paste resume text and CareerPilot detects known skills locally (never sent to any API) and merges them into your profile.
- **Pagination:** optionally follows SerpApi's `next_page_token` for up to three pages per query.
- **Quota-saving cache:** identical SerpApi requests within 15 minutes are reused (scoped per API key) and reported separately from billable calls.
- Sort by fit, freshness, or evidence strength; keyword filter; duplicate-listing counts and alternate application sources.
- Tracker notes (follow-ups, contacts, interview prep) and tracker CSV export.
- Headless CLI: `python careerpilot.py "AI Engineer" --location India --skills "Python, RAG" [--json]`.
- Unit tests that run offline without using API quota.

## Quick start — Windows PowerShell

Use Python 3.11 or newer. From the repository folder:

    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    Copy-Item .env.example .env

Open .env and set your SerpApi key:

    SERPAPI_API_KEY=your_real_key_here

Run the app:

    streamlit run app.py

If PowerShell blocks environment activation, try a new Command Prompt and activate with .venv\Scripts\activate.bat, or invoke the venv's Python directly.

### Linux / macOS

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    cp .env.example .env
    streamlit run app.py

### Explore without API keys

Start the app and select **Explore demo workspace**. It makes no network requests and uses fictional examples for checking the UI, scoring, and tracker. Do not use synthetic demo mode as evidence that live search works in the hackathon video.

## Optional Gemini query planner

The core app only requires SerpApi. To add model-assisted planning, place a Google AI Studio key in .env:

    GEMINI_API_KEY=your_gemini_key_here
    GEMINI_MODEL=gemini-3.6-flash

The planner can suggest relevant query variants, but the app checks query length, role-token relevance, duplicates, and query count before they are used. If the model request fails, the agent falls back to deterministic planning. Model access and quota depend on your Google account and model; this feature is optional.

## How to use the app

1. Enter your target role, preferred location, work mode, skills, and years of relevant experience.
2. Add a SerpApi key in the sidebar or load it from .env.
3. Choose search depth and how many top results to cross-check.
4. Click **Run live agent search**.
5. Inspect job details, matched/missing skill mentions, score components, evidence labels, and source links.
6. Save roles to the application tracker, change their status, and export the live shortlist as CSV.

## Command-line usage

The same agent runs without the UI, which is useful for scripting, cron jobs, or piping results into other tools. It reads `SERPAPI_API_KEY` (and the optional `GEMINI_API_KEY` / `GEMINI_MODEL`) from the environment or `.env`.

    python careerpilot.py "AI Engineer" --location India --skills "Python, FastAPI, RAG"

| Option | Default | Description |
| --- | --- | --- |
| `role` (positional) | — | Target role, e.g. `"AI Engineer"` |
| `--location` | `India` | Preferred location; `Anywhere` disables the location filter |
| `--skills` | empty | Comma-separated skills used for fit scoring and skill-gap analysis |
| `--work-mode` | `Any` | `Any`, `Remote`, `Hybrid`, or `On-site` |
| `--experience` | `0` | Years of relevant experience (affects seniority fit) |
| `--depth` | `2` | Google Jobs query variants (1–3) |
| `--pages` | `1` | Result pages per query via `next_page_token` (1–3) |
| `--verify` | `3` | Top results to cross-check with Google Search (0–8) |
| `--json` | off | Print the full run (jobs, trace, query plan, insights, warnings) as JSON |

The default output prints the agent trace, the top 15 ranked jobs with fit score, evidence status, and link, followed by in-demand skills missing from your profile. A run makes at most `depth × pages + verify` SerpApi requests; repeated identical requests within the same process are served from cache.

Examples:

    # Remote roles, more results, no cross-checks (fewer credits)
    python careerpilot.py "Data Scientist" --work-mode Remote --pages 2 --verify 0

    # Save machine-readable output
    python careerpilot.py "ML Engineer" --skills "PyTorch, MLOps" --json > results.json

## Architecture

    Candidate profile
        ↓
    Query planner (optional Gemini, or deterministic fallback)
        ↓
    SerpApi Google Jobs → normalized listings
        ↓
    Duplicate merger → explainable fit scorer
        ↓
    SerpApi Google Search → evidence check
        ↓
    Shortlist → CSV export / SQLite tracker

Key files:
- **app.py** — Streamlit interface, result cards, tracker, CSV export, trace.
- **careerpilot.py** — SerpApi client, job normalization, query plan, scoring, deduplication, evidence checks.
- **llm_agent.py** — optional Gemini planner with output validation.
- **storage.py** — SQLite saved-job and application-status persistence.
- **demo_data.py** — fictional offline samples.
- **tests/test_core.py** — offline tests.

## Score and evidence labels

The score is a **ranking heuristic**, not a hiring probability. The breakdown is displayed for each result. “Missing skills” means that a term was not found in the indexed title/description; it does not prove the candidate lacks the skill or that the job does not require it.

Evidence labels are intentionally conservative:
- **Likely employer-controlled careers page found:** domain and career-path signals matched a web result; the vacancy may still be stale.
- **Related result found; employer page not confirmed:** a potentially relevant result was found but employer ownership was not confidently matched.
- **Application source surfaced:** Google Jobs supplied an application option; review it before use.
- **Needs manual verification:** evidence was unavailable or weak.

Domain matching is a heuristic. Some genuine employer ATS pages will not be detected, and some search results may be stale. Users must review sources manually.

## Search budget and reliability

- Up to three Google Jobs queries are allowed per run, each with up to three result pages.
- Repeated identical requests within 15 minutes are served from an in-memory cache and are not counted as SerpApi calls.
- Up to eight top results can be checked through Google Search.
- SerpApi request counts are shown in the UI; Gemini requests are counted separately.
- If one query fails, the agent records a warning and continues where possible.
- A live-search failure is never silently replaced with sample data.

## Privacy and security

- Keep real keys in .env or the password field in the sidebar. Never commit keys to GitHub.
- .gitignore excludes .env, local SQLite databases, virtual environments, and caches.
- Only role-search profile fields are sent for planning/search; do not enter sensitive personal data.
- Saved roles and statuses are stored locally at data/careerpilot.db by default. Set CAREERPILOT_DB to select another writable path.
- CareerPilot does not submit applications, message recruiters, or access gated websites.
- All search-result text is treated as untrusted: it is HTML-escaped or Markdown-escaped before rendering, links are restricted to `http(s)` URLs, and CSV exports neutralize spreadsheet formulas (`=`, `+`, `-`, `@`).
- Keys from `.env` are used server-side only and are never pre-filled into the sidebar fields, so a deployed app cannot reveal the owner's key to visitors.
- The Gemini model name is validated before being placed in the API URL; network errors are reported without echoing request details.
- The SQLite tracker is a single local file. If you deploy the app publicly, every visitor shares it — keep deployments personal or add authentication.

## Tests

These tests do not call SerpApi or Gemini and do not use API quota:

    python -m unittest discover -s tests -v

## Hackathon submission checklist

The official rules require a public GitHub repository, a complete website submission, and an accessible demo video shorter than three minutes. A saved draft does not count as submitted.

- Recommended track: **AI Agents**.
- Explain how Google Jobs and Google Search materially support the workflow.
- Record a real local live run; verify the video opens in a private/incognito browser window.
- Disclose AI development tools as required. ChatGPT assisted in drafting this implementation; review and understand the code before submitting.
- Answer project-history/prior-work questions truthfully.
- Do not expose keys or personal information in source code or demo recording.

Official links: [Hackathon page](https://serpapi.github.io/serpapi-india-hackathon-2026/) · [Rules](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html) · [SerpApi docs](https://serpapi.com/search-api)
