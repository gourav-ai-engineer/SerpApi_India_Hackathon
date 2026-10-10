# CareerPilot AI — Voice-over Script

The demo video's narration, one block per chapter of `tools/record_demo.py`. The same text lives in `tools/narration.py`, which turns it into an **AI voice-over** with Kokoro, an open-source text-to-speech model that runs offline (voice `am_michael`).

## One command: narrated video

    streamlit run app.py                                  # terminal 1, key in .env
    python -m pip install -r requirements-video.txt       # terminal 2, once
    python -m playwright install chromium                 # once
    python tools/record_demo.py --practice --voice        # rehearsal with demo data
    python tools/record_demo.py --voice                   # LIVE narrated video to submit

The first `--voice` run downloads the Kokoro model (~350 MB) from GitHub and generates the narration clips. The recorder then holds each chapter on screen until its narration ends, and mixes the voice in at each chapter's start time. The result is `recordings/careerpilot_demo.mp4`, a single file with the voice built in, ready for YouTube. The practice run lasts about 2:41. A live run adds any search time beyond the narration of chapter 4, and the script warns you if the result reaches 3:00.

To change the wording, edit `SCRIPT` in `tools/narration.py`, delete `recordings/narration/`, and re-run. To use your own voice instead, record these lines yourself and leave out `--voice`.

**Disclosure:** the narration is AI-generated. This is listed in SUBMISSION.md's AI tools section.

## Script

### 1 Hook
> Job hunting means duplicated, stale listings, and no idea why a role fits you. CareerPilot is an AI agent that fixes that, using live data from SerpApi.

### 2 Keys and search budget
> API keys stay on the server and never appear in the page. In the sidebar, I set the agent's budget: queries, result pages, and cross-checks.

### 3 Profile and resume skills
> I enter my target role and location, then paste my resume. Skills are detected locally, nothing is uploaded, and added to my profile.

### 4 Agent run
> Now the agent plans its queries, searches Google Jobs through SerpApi, follows pagination, merges duplicates, ranks every role, and verifies the top results.

### 5 Run summary
> The summary shows unique roles, strong fits, and the exact number of SerpApi calls. Repeat searches are cached, so credits aren't wasted.

### 6 Job card
> Each job gets a colour-coded fit score, the skills it matched, and an evidence badge.

### 7 Score breakdown and sources
> The score explains itself: role, skills, location, seniority, and freshness. It's a ranking aid, not a hiring prediction.

### 8 Filters and sorting
> I can filter by fit score, search by keyword, or sort by evidence. For top results, a second SerpApi search on Google looks for the employer's own careers page. Anything uncertain is clearly labelled, never hidden.

### 9 Export
> The shortlist exports to CSV, safe for Excel.

### 10 Market insights
> Market insights turn these listings into advice. Green skills, I already have. Blue skills are gaps worth learning next. It also shows who is hiring most.

### 11 Application tracker
> I save a promising role to my tracker, update its status, and add a follow-up note. It all stays on my machine and exports to CSV.

### 12 Agent trace
> The agent trace records every query, page, and check, so every decision is reviewable.

### 13 Method and limits
> Scoring weights, evidence labels, and known limits are documented in the app.

### 14 Close
> CareerPilot: live discovery with SerpApi, verified evidence, explainable ranking, and skill-gap insights. It even runs from the command line. Thanks for watching!
