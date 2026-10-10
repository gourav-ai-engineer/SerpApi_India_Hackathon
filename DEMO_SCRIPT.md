# CareerPilot Demo Recording Plan (target: 2 minutes 50 seconds)

The official demo must be shorter than three minutes and should show the app running locally. Use a real SerpApi run for the recorded submission; the synthetic demo workspace is only a fallback for practicing the interface.

## Before recording

- Start the app locally with the command shown in the README.
- Put a valid SerpApi key in the sidebar or load it from .env.
- Use a broad target such as AI Engineer, location India, skills Python / FastAPI / PyTorch / RAG / LLMs.
- Set query variants to 2, result pages per query to 1, and cross-check top results to 2 or 3 so the API usage and runtime remain manageable.
- Have a short resume excerpt ready to paste (skills paragraph only; no phone number, email, or address).
- Open a second terminal in the project folder with the venv active, and pre-type (don't run) `python careerpilot.py "AI Engineer" --skills "Python, RAG" --depth 1 --verify 0`. Use a large font. The app's earlier search warms the cache only inside the app process, so the CLI run makes one real request; trim any wait in editing.
- Save one role to the tracker beforehand so the tracker isn't empty if you're short on time.
- Close terminals or editors that might reveal secrets. Keep the sidebar's API-key field masked.
- Run the live search once before recording to confirm the API key works and that results are returned.

## Timeline

**0:00–0:15 — Problem and profile**  
Describe the problem: job seekers get duplicated, stale, poorly explained listings. Show the profile fields.

**0:15–0:30 — Resume skill detection**  
Expand *Paste resume text to auto-detect skills*, paste the excerpt, and click *Add detected skills to profile*. Mention that the resume is analysed locally and never sent to any API.

**0:30–0:55 — Agent planning and discovery**  
Click *Run live agent search*. Point to the success banner: SerpApi request count and cached responses. Mention that Google Jobs supplies structured listings, and that repeated identical searches are reused to save credits.

**0:55–1:30 — Explainable ranking**  
Use *Sort by* and the keyword filter briefly. Open a top result: fit-score breakdown, matched skills, posting age, the "seen in N listings" duplicate count, and other application sources. State that the score is a ranking aid, not a hiring probability.

**1:30–1:50 — Evidence checks**  
Switch *Sort by* to *Evidence strength*. Open one result's evidence note and source link. Explain the labels (likely employer careers page / related result / manual verification needed): the app reports uncertainty instead of claiming every indexed job is open.

**1:50–2:15 — Market insights**  
Open *Market insights*: most-requested skills chart, **your skill gaps** with the share of listings asking for each, top hiring companies, and remote/salary/freshness shares. This is the "what should I learn next" moment.

**2:15–2:30 — Save and track**  
Save a role, open *Application tracker*, set it to Applied, add a follow-up note, and show the tracker CSV export.

**2:30–2:42 — Same agent, no UI**  
Switch to the terminal and run the pre-typed command. Point to the trace lines, the ranked jobs with evidence status, and the skill-gap line at the end. Say: "The same agent runs headless — `--json` makes it scriptable for cron jobs or other tools."

**2:42–2:50 — Close**  
Show the *Agent trace* (plan → search → pages → rank → check → report). Close with the differentiator: live structured discovery + independent search evidence + explainable ranking + skill-gap insights + a usable tracker, in the browser or the terminal.

## Recording checks

- Keep the full recording below 3:00.
- Show a real live run, not only synthetic examples.
- Make the link publicly accessible or unlisted without requiring the judge to request access.
- The sidebar key field should read "Using key from .env" or stay masked; never click the eye icon while recording.
- Do not show the API key, private email, local secrets, or unrelated personal files.
