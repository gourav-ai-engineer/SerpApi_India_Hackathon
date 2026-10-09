# CareerPilot Demo Recording Plan (target: 2 minutes 40 seconds)

The official demo must be shorter than three minutes and should show the app running locally. Use a real SerpApi run for the recorded submission; the synthetic demo workspace is only a fallback for practicing the interface.

## Before recording

- Start the app locally with the command shown in the README.
- Put a valid SerpApi key in the sidebar or load it from .env.
- Use a broad target such as AI Engineer, location India, skills Python / FastAPI / PyTorch / RAG / LLMs.
- Set query variants to 2 and cross-check top results to 2 or 3 so the API usage and runtime remain manageable.
- Close terminals or editors that might reveal secrets. Keep the sidebar's API-key field masked.
- Run the live search once before recording to confirm the API key works and that results are returned.

## Timeline

**0:00–0:15 — Problem and profile**  
Show CareerPilot and describe the problem: job seekers receive duplicated, stale, poorly explained listings. Point to the profile fields and the two SerpApi-backed steps.

**0:15–0:40 — Agent planning and discovery**  
Click Run live agent search. Show the live request count, query plan, and result count. Mention that Google Jobs supplies structured listing data rather than manually maintained sample records.

**0:40–1:20 — Explainable ranking**  
Open a top result. Show the fit score breakdown, skill mentions, posting-age signal, application link, and duplicate removal in the agent trace. State that the score is a ranking aid, not a hiring probability.

**1:20–1:55 — Evidence checks**  
Open the evidence explanation and link for one result. Show the label: likely employer-careers page, related result, or manual verification needed. Emphasize that the app reports evidence and uncertainty instead of claiming every indexed job is active.

**1:55–2:20 — Save and track**  
Save a role. Open Application tracker, update it to Applied, then show that the status persists in SQLite.

**2:20–2:40 — Export and close**  
Show the CSV export control and Agent trace. Close with the differentiator: live structured discovery + independent search evidence + explainable ranking + a usable application tracker.

## Recording checks

- Keep the full recording below 3:00.
- Show a real live run, not only synthetic examples.
- Make the link publicly accessible or unlisted without requiring the judge to request access.
- Do not show the API key, private email, local secrets, or unrelated personal files.
