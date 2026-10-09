"""Streamlit interface for CareerPilot AI."""
from __future__ import annotations

import csv
import io
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from careerpilot import CareerPilotAgent, score_job
from demo_data import SAMPLE_JOBS
from storage import VALID_STATUSES, list_saved_jobs, remove_saved_job, save_job, update_job_status

load_dotenv()

st.set_page_config(
    page_title="CareerPilot AI · Job Intelligence",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp { background: #0b1020; color: #eef2ff; }
      [data-testid="stSidebar"] { background: #10182b; border-right: 1px solid #26334f; }
      [data-testid="stHeader"] { background: rgba(11,16,32,.92); }
      .hero { padding: 1.2rem 1.4rem; border: 1px solid #293955; border-radius: 18px;
              background: linear-gradient(115deg,#15243e 0%,#12172a 58%,#1b1931 100%);
              margin-bottom: 1rem; }
      .eyebrow { text-transform: uppercase; letter-spacing: .13em; font-size: .76rem;
                 color: #9fb8ff; font-weight: 700; }
      .muted { color: #aab6cf; }
      .job-meta { color: #aab6cf; font-size: .92rem; }
      .tag { display: inline-block; padding: .2rem .55rem; margin: .15rem .22rem .15rem 0;
             border: 1px solid #334566; border-radius: 999px; color: #c9d8ff; font-size: .78rem; }
      div[data-testid="stMetric"] { background: #121b30; border: 1px solid #273653;
                                    padding: .8rem; border-radius: 12px; }
      div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #273653 !important; }
      .small-note { color: #aab6cf; font-size: .83rem; }
      h1, h2, h3 { letter-spacing: -.025em; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "careerpilot_run" not in st.session_state:
    st.session_state.careerpilot_run = None
if "careerpilot_error" not in st.session_state:
    st.session_state.careerpilot_error = None

with st.sidebar:
    st.markdown("## 🧭 CareerPilot")
    st.caption("Evidence-driven job intelligence")
    st.divider()
    env_key = os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY") or ""
    api_key = st.text_input(
        "SerpApi API key",
        value=env_key,
        type="password",
        help="Used in this session for live Google Jobs and Google Search requests. Never stored in the tracker.",
    )
    st.markdown("[Get a SerpApi key ↗](https://serpapi.com/)")
    st.divider()
    st.markdown("**Agent budget**")
    search_depth = st.slider(
        "Google Jobs query variants",
        min_value=1,
        max_value=3,
        value=2,
        help="Each query can consume a SerpApi search. Exact cached requests may be free under SerpApi's cache policy.",
    )
    verify_top_n = st.slider(
        "Cross-check top results",
        min_value=0,
        max_value=8,
        value=3,
        help="Adds Google Search calls to look for employer-careers evidence. No search result can guarantee a vacancy is still open.",
    )
    st.divider()
    st.markdown(
        "<div class='small-note'>Built with SerpApi Google Jobs + Google Search. "
        "No LLM key is required for the core agent. Ranking is explainable and deterministic.</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Live search · Explainable ranking · Evidence checks</div>
      <h1 style="margin:.35rem 0 .2rem 0;">Find your next role with proof, not noise.</h1>
      <p class="muted" style="max-width:850px;margin-bottom:.15rem;">
        CareerPilot plans targeted searches, merges duplicate listings, ranks roles against
        your profile, and searches for employer-careers evidence. It reports uncertainty instead
        of pretending a search snippet proves a job is still open.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Profile fields are kept in Streamlit session state only; the tracker stores saved job details.
left, right = st.columns([1, 1])
with left:
    role = st.text_input("Target role", value="AI Engineer", key="profile_role")
    location = st.text_input("Preferred location", value="India", key="profile_location")
    work_mode = st.selectbox("Work preference", ["Any", "Remote", "Hybrid", "On-site"], index=0, key="profile_mode")
with right:
    skills_text = st.text_area(
        "Skills to match (comma-separated)",
        value="Python, FastAPI, PyTorch, RAG, LLMs",
        height=92,
        key="profile_skills",
    )
    experience_years = st.number_input(
        "Relevant experience (years)",
        min_value=0,
        max_value=40,
        value=0,
        step=1,
        key="profile_experience",
    )

profile = {
    "role": role.strip(),
    "location": location.strip(),
    "work_mode": work_mode,
    "skills": skills_text,
    "experience_years": int(experience_years),
}

action_a, action_b, action_c = st.columns([1.2, 1, 2])
with action_a:
    live_clicked = st.button("🔎 Run live agent search", type="primary", use_container_width=True)
with action_b:
    demo_clicked = st.button("✨ Explore demo workspace", use_container_width=True)
with action_c:
    st.caption("Live mode uses SerpApi. Demo mode uses fictional examples and never represents live vacancies.")

if live_clicked:
    if not api_key.strip():
        st.session_state.careerpilot_error = "Add your SerpApi key in the sidebar to run live searches, or use the synthetic demo workspace."
    elif not profile["role"]:
        st.session_state.careerpilot_error = "Enter a target role before starting a search."
    else:
        try:
            with st.spinner("The agent is planning queries, searching jobs, ranking matches, and checking evidence…"):
                agent = CareerPilotAgent(api_key)
                result = agent.run(profile, search_depth=search_depth, verify_top_n=verify_top_n)
                result["mode"] = "live"
                result["run_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
                st.session_state.careerpilot_run = result
                st.session_state.careerpilot_error = None
        except Exception as exc:
            st.session_state.careerpilot_error = f"Live search failed: {exc}"

if demo_clicked:
    examples = [score_job(dict(job), profile) for job in SAMPLE_JOBS]
    examples.sort(key=lambda item: int(item.get("score", 0)), reverse=True)
    st.session_state.careerpilot_run = {
        "jobs": examples,
        "trace": [
            "DEMO: loaded fictional examples from demo_data.py; no web request was made.",
            "PLAN: would expand the target role into up to three distinct search queries in live mode.",
            "RANK: calculated explainable role, skill, location/work-mode, seniority, and freshness signals.",
            "GUARDRAIL: these records are synthetic UI examples, not real or open vacancies.",
        ],
        "query_plan": [],
        "api_calls": 0,
        "warnings": [],
        "profile": dict(profile),
        "mode": "demo",
        "run_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    st.session_state.careerpilot_error = None

if st.session_state.careerpilot_error:
    st.error(st.session_state.careerpilot_error)

run = st.session_state.careerpilot_run
if run:
    jobs = run.get("jobs", [])
    mode = run.get("mode", "demo")
    if mode == "demo":
        st.warning("DEMO MODE — every job below is fictional sample data. Switch to live mode with a SerpApi key for real search results.")
    else:
        st.success(f"Live SerpApi run complete · {run.get('api_calls', 0)} request(s) · {run.get('run_at', '')}")

    verified_count = sum(
        1 for job in jobs
        if "careers page found" in str(job.get("verification_status", "")).casefold()
        or "corroboration" in str(job.get("verification_status", "")).casefold()
    )
    high_fit_count = sum(1 for job in jobs if int(job.get("score", 0)) >= 75)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Unique roles", len(jobs))
    metric_cols[1].metric("Strong fit (75+)", high_fit_count)
    metric_cols[2].metric("Evidence leads", verified_count if mode == "live" else "—")
    metric_cols[3].metric("Search calls", run.get("api_calls", 0) if mode == "live" else "0 (demo)")
    if run.get("warnings"):
        with st.expander(f"Search warnings ({len(run['warnings'])})", expanded=False):
            for warning in run["warnings"]:
                st.warning(warning)

    tab_discover, tab_tracker, tab_trace, tab_method = st.tabs(
        ["🎯 Discover", "📌 Application tracker", "🧠 Agent trace", "ℹ️ Method & limits"]
    )

    with tab_discover:
        if not jobs:
            st.info("No jobs were returned. Try a broader role title, change the location, or lower the number of cross-checks.")
        else:
            min_score = st.slider("Minimum fit score", 0, 100, 0, 5, key="min_fit_score")
            filtered_jobs = [job for job in jobs if int(job.get("score", 0)) >= min_score]
            st.caption(f"Showing {len(filtered_jobs)} of {len(jobs)} unique results, ranked by explainable fit score.")
            if mode == "live":
                csv_buffer = io.StringIO()
                columns = [
                    "title", "company", "location", "posted_at", "salary", "score",
                    "matched_skills", "missing_skills", "verification_status", "apply_url",
                    "share_url", "evidence_url",
                ]
                writer = csv.DictWriter(csv_buffer, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                for job in filtered_jobs:
                    row = dict(job)
                    row["matched_skills"] = ", ".join(row.get("matched_skills", []))
                    row["missing_skills"] = ", ".join(row.get("missing_skills", []))
                    writer.writerow(row)
                st.download_button(
                    "⬇️ Export shortlist as CSV",
                    data=csv_buffer.getvalue(),
                    file_name="careerpilot_shortlist.csv",
                    mime="text/csv",
                )

            for index, job in enumerate(filtered_jobs, start=1):
                with st.container(border=True):
                    header, score_col = st.columns([5, 1])
                    with header:
                        st.markdown(f"### {index}. {job.get('title', 'Untitled role')}")
                        st.markdown(
                            f"<div class='job-meta'><b>{job.get('company', 'Company not listed')}</b>"
                            f" · {job.get('location', 'Location not listed')}</div>",
                            unsafe_allow_html=True,
                        )
                        badges = []
                        if job.get("posted_at"):
                            badges.append(str(job.get("posted_at")))
                        if job.get("schedule_type"):
                            badges.append(str(job.get("schedule_type")))
                        if job.get("salary"):
                            badges.append(str(job.get("salary")))
                        if badges:
                            st.caption(" · ".join(badges))
                    with score_col:
                        st.metric("FIT", f"{int(job.get('score', 0))}%")
                    st.progress(max(0, min(100, int(job.get("score", 0)))) / 100)
                    matched = job.get("matched_skills") or []
                    missing = job.get("missing_skills") or []
                    if matched:
                        st.markdown("**Matched skills:** " + " · ".join(f"‘{skill}’" for skill in matched[:10]))
                    if missing:
                        st.caption("Profile skills not seen in this listing (not necessarily absent from the actual role): " + ", ".join(missing[:8]))
                    status = str(job.get("verification_status") or "Not independently checked")
                    st.markdown(f"**Evidence status:** {status}")
                    description = str(job.get("description") or "")
                    if description:
                        with st.expander("Role details and score explanation"):
                            st.write(description[:1800] + ("…" if len(description) > 1800 else ""))
                            breakdown = job.get("score_breakdown") or {}
                            if breakdown:
                                st.markdown("**Score components**")
                                for label, value in breakdown.items():
                                    st.write(f"- {label}: {value}/100")
                            for reason in job.get("fit_reasons", []):
                                st.write(f"- {reason}")
                            st.markdown("**Evidence note**")
                            st.write(job.get("evidence_snippet") or "No independent source snippet available.")
                            if job.get("evidence_url") and mode == "live":
                                st.markdown(f"[Open evidence source ↗]({job['evidence_url']})")
                            if job.get("source_name"):
                                st.caption(f"Search source: {job.get('source_name')}")
                    job_actions = st.columns([1, 1, 4])
                    with job_actions[0]:
                        if st.button("Save to tracker", key=f"save-{job.get('job_id')}", use_container_width=True):
                            try:
                                save_job(job)
                                st.toast("Saved to application tracker.")
                            except Exception as exc:
                                st.error(f"Could not save job: {exc}")
                    with job_actions[1]:
                        apply_url = str(job.get("apply_url") or "")
                        share_url = str(job.get("share_url") or "")
                        target_url = apply_url or (share_url if mode == "live" else "")
                        if target_url and mode == "live":
                            st.link_button("Open source ↗", target_url, use_container_width=True)
                        elif mode == "demo":
                            st.button("Sample only", key=f"sample-{job.get('job_id')}", disabled=True, use_container_width=True)
                        else:
                            st.button("No direct link", key=f"nolink-{job.get('job_id')}", disabled=True, use_container_width=True)

    with tab_tracker:
        st.markdown("### Your saved roles")
        st.caption("Status changes are stored locally in SQLite on this machine.")
        saved = list_saved_jobs()
        if not saved:
            st.info("No saved jobs yet. Choose “Save to tracker” on a role in Discover.")
        else:
            tracker_counts = {status: sum(1 for item in saved if item.get("status") == status) for status in VALID_STATUSES}
            cols = st.columns(len(VALID_STATUSES))
            for col, status in zip(cols, VALID_STATUSES):
                col.metric(status, tracker_counts.get(status, 0))
            for job in saved:
                with st.container(border=True):
                    top, status_col, remove_col = st.columns([4, 2, 1])
                    with top:
                        st.markdown(f"**{job.get('title', 'Untitled role')}**")
                        st.caption(f"{job.get('company', 'Unknown company')} · {job.get('location', 'Location not listed')}")
                        if job.get("is_demo"):
                            st.caption("DEMO record — fictional sample")
                        elif job.get("apply_url"):
                            st.markdown(f"[Application source ↗]({job['apply_url']})")
                    with status_col:
                        current = job.get("status", "Saved")
                        status_index = VALID_STATUSES.index(current) if current in VALID_STATUSES else 0
                        selected_status = st.selectbox(
                            "Application status",
                            VALID_STATUSES,
                            index=status_index,
                            key=f"status-{job.get('job_id')}",
                        )
                        if selected_status != current:
                            update_job_status(str(job.get("job_id")), selected_status)
                            st.rerun()
                    with remove_col:
                        st.write("")
                        if st.button("Remove", key=f"remove-{job.get('job_id')}"):
                            remove_saved_job(str(job.get("job_id")))
                            st.rerun()

    with tab_trace:
        st.markdown("### What the agent did")
        st.caption("The trace makes the search plan and evidence decisions reviewable.")
        for event in run.get("trace", []):
            st.write("• " + str(event))
        if run.get("query_plan"):
            st.markdown("**Query plan**")
            for query in run["query_plan"]:
                st.code(query, language="text")
        st.caption(f"Run started: {run.get('run_at', 'Demo session')}")

    with tab_method:
        st.markdown("### What the score means")
        st.write(
            "Fit score is a transparent ranking heuristic, not a probability of being hired. "
            "It weights role-title alignment (35%), declared-skill mentions (38%), location and work mode (15%), "
            "seniority fit (7%), and the posting-age signal (5%). The score does not know your full CV, interview "
            "performance, or an employer's real hiring rubric."
        )
        st.markdown("### Evidence labels")
        st.write(
            "- **Likely employer-controlled careers page found:** a web result matched company-domain and careers-page signals. "
            "This still does not prove the vacancy is currently open.\n"
            "- **Related result found:** search found a potentially relevant result, but the employer-controlled domain was not confirmed.\n"
            "- **Application source surfaced:** Google Jobs supplied an application option; check that it is current and legitimate.\n"
            "- **Needs manual verification:** evidence was missing or weak."
        )
        st.markdown("### Data handling")
        st.write(
            "The SerpApi key is used only for the live request in this app session and is not written to the SQLite tracker. "
            "Saved job details and statuses are stored locally in data/careerpilot.db. Do not commit .env or database files."
        )
        st.markdown("### Known limitations")
        st.write(
            "Search results can be stale, duplicated, sponsored, incomplete, or inaccurate. Domain matching is a heuristic. "
            "This app does not contact employers, submit applications, scrape gated systems, or verify that a recruiter is genuine. "
            "Always inspect the actual employer page before sharing personal information or applying."
        )
else:
    st.markdown("---")
    info_a, info_b, info_c = st.columns(3)
    info_a.markdown("#### 1 · Discover\nLive structured job results from SerpApi Google Jobs.")
    info_b.markdown("#### 2 · Investigate\nSearch for employer-careers evidence and keep the source link.")
    info_c.markdown("#### 3 · Act\nSave promising roles, track statuses, and export a live shortlist.")
    st.info("Start a live search with a SerpApi key, or explore the clearly labelled synthetic demo workspace first.")
