# CareerPilot AI — Voice-over Script

This script matches the 14 chapters recorded by `tools/record_demo.py`. In a practice run the video lasts about 2:28. A live run is longer by however long the search takes (usually 10–30 seconds), which lands around 2:40–2:55. The limit is under 3:00.

**How to use it**

1. Record the live video: `python tools/record_demo.py`. It also writes `recordings/careerpilot_demo.chapters.txt` with the real start time of each chapter.
2. Add about 4 seconds to each chapter time; the video starts while the page is still loading.
3. Record your narration in any editor (Clipchamp on Windows, CapCut or DaVinci Resolve), starting each block at its chapter time.
4. If the live search runs long, cut the wait in chapter 4 so the total stays under 3:00.

Each block is about 2.3 words per second, a calm pace. If you run long, skip the lines marked *(optional)*.

---

### 1 · Hook · 0:00 (10 s)
> Job hunting today means duplicated, stale listings and no idea why a role fits you. CareerPilot is an AI agent that fixes that, built on live SerpApi data.

### 2 · Keys and search budget · ~0:10 (10 s)
> API keys stay on the server and are never shown in the page. In the sidebar I control the agent's budget: how many queries, how many result pages, and how many results to cross-check.

### 3 · Profile and resume skills · ~0:20 (11 s)
> I set my target role, location and experience. I can also paste my resume. CareerPilot detects my skills locally, without uploading anything, and adds them to my profile.

### 4 · Agent run · ~0:31 (3 s + search time)
> Now the agent runs. It plans queries, searches Google Jobs through SerpApi, follows pagination, merges duplicate listings, ranks every role, and verifies the top results.

*(If the search takes a while, add:)* "This is a live search, so nothing is pre-loaded."

### 5 · Run summary · ~0:34 (10 s)
> Here's the summary: unique roles, strong fits, evidence leads, and the exact number of SerpApi calls. Identical searches are cached for fifteen minutes, so re-running doesn't waste credits.

### 6 · Job card · ~0:44 (11 s)
> Every job gets a colour-coded fit score, the skills it matched, and an evidence badge. Green skills appear in the listing; grey ones weren't mentioned.

### 7 · Score breakdown and sources · ~0:55 (11 s)
> The score explains itself: role alignment, skills, location, seniority and how fresh the posting is. It's a ranking aid, not a hiring prediction, and the sources are always shown.

### 8 · Filters and sorting · ~1:06 (18 s)
> I can filter by minimum fit score, search by keyword, or sort by evidence strength. For the top results the agent ran a second SerpApi search, on Google Search, looking for the employer's own careers page. Strong evidence comes first, and anything uncertain is labelled as needing manual checks. It's never hidden.

### 9 · Export · ~1:24 (4 s)
> The shortlist exports to CSV, safely formatted for Excel.

### 10 · Market insights · ~1:28 (16 s)
> Market insights turn the live results into advice. Green skills are ones I already have; blue skills are gaps that show up across these listings, so I know exactly what to learn next. It also shows which companies are hiring most for this role.

### 11 · Application tracker · ~1:44 (16 s)
> When I find a good role I save it to my tracker. I can move it through Saved, Applied, Interview and Offer, and keep notes like follow-up dates. Everything stays on my machine and exports to CSV.

### 12 · Agent trace · ~2:00 (7 s)
> The agent trace shows every step: each query, page, verification and warning, so the agent's decisions are fully reviewable.

### 13 · Method and limits · ~2:07 (6 s)
> And the method is documented: scoring weights, evidence labels, data handling and known limits.

### 14 · Close · ~2:13 (11 s)
> CareerPilot: live job discovery with SerpApi, verified evidence, explainable ranking and skill-gap insights. It also runs from the command line for scripting. Thanks for watching!

---

## Tips

- **Before recording:** speak slowly, record in a quiet room, and keep the mic close. Read each block out loud once before recording.
- **Live data changes:** if your live run shows no green "employer careers page" badges, say "the agent shows what it found and flags what it couldn't verify" instead of claiming strong evidence.
- **Optional command-line clip (+10 s):** if you have time to spare, add the clip from `DEMO_SCRIPT.md` before chapter 14 and say: "The same agent runs headless from the terminal, with JSON output for scripting."
- **Captions:** the on-screen captions repeat your key points, so the video still works muted.
