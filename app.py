"""Streamlit interface for CareerPilot AI."""
from __future__ import annotations

import csv
import io
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from careerpilot import CareerPilotAgent, extract_skills_from_text, market_insights, score_job
from demo_data import SAMPLE_JOBS
from safety import csv_safe, escape_html, escape_markdown as md, safe_http_url
from storage import (
    VALID_STATUSES, list_saved_jobs, remove_saved_job, save_job, update_job_notes, update_job_status,
)

load_dotenv()

st.set_page_config(
    page_title="CareerPilot AI · Job Intelligence",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="auto",  # Expanded on desktop, collapsed on phones so it doesn't cover the app.
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap');
      :root {
        --bg: #070b16; --surface: #0e1424; --surface-2: #131b30; --line: #222d47; --line-2: #2e3b5c;
        --text: #eef2ff; --muted: #9aa7c4; --accent: #7c9cff; --accent-2: #a78bfa;
        --good: #34d399; --warn: #fbbf24; --bad: #f87171;
      }
      html, body, .stApp, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
      .stApp {
        color: var(--text);
        background:
          radial-gradient(900px 500px at 85% -10%, rgba(124,156,255,.14), transparent 60%),
          radial-gradient(700px 420px at -10% 10%, rgba(167,139,250,.10), transparent 60%),
          var(--bg);
      }
      [data-testid="stHeader"] { background: transparent; }
      [data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--line); }
      .block-container { padding-top: 2rem; max-width: 1280px; }
      h1, h2, h3, h4 { letter-spacing: -.025em; font-weight: 700; }
      code, pre { font-family: 'JetBrains Mono', monospace !important; }

      .hero { position: relative; overflow: hidden; padding: 2rem 2.2rem; margin-bottom: 1.4rem;
              border: 1px solid var(--line-2); border-radius: 22px;
              background: linear-gradient(135deg, rgba(124,156,255,.16), rgba(167,139,250,.08) 45%, rgba(14,20,36,.9)); }
      .hero::after { content: ""; position: absolute; right: -80px; top: -80px; width: 280px; height: 280px;
                     border-radius: 50%; background: radial-gradient(circle, rgba(124,156,255,.35), transparent 70%); }
      .hero h1 { font-size: clamp(1.8rem, 3.2vw, 2.6rem); font-weight: 800; margin: .5rem 0 .4rem;
                 background: linear-gradient(90deg, #fff, #c7d2fe 60%, #ddd6fe);
                 -webkit-background-clip: text; background-clip: text; color: transparent; }
      .eyebrow { display: inline-flex; gap: .5rem; align-items: center; text-transform: uppercase;
                 letter-spacing: .14em; font-size: .72rem; font-weight: 700; color: #c7d2fe;
                 padding: .3rem .7rem; border-radius: 999px; border: 1px solid var(--line-2);
                 background: rgba(124,156,255,.08); }
      .eyebrow .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--good);
                      box-shadow: 0 0 10px var(--good); }
      .muted { color: var(--muted); }
      .hero-steps { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }
      .hero-steps span { font-size: .8rem; color: var(--muted); padding: .25rem .65rem;
                         border-radius: 8px; background: rgba(255,255,255,.04); border: 1px solid var(--line); }

      div[data-testid="stMetric"] { background: var(--surface-2); border: 1px solid var(--line);
                                    padding: .9rem 1rem; border-radius: 14px; }
      div[data-testid="stMetricValue"] { font-weight: 800; }
      div[data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--line) !important; border-radius: 16px !important;
                                                        background: rgba(14,20,36,.65); transition: border-color .15s, transform .15s; }
      div[data-testid="stVerticalBlockBorderWrapper"]:hover { border-color: var(--line-2) !important; }

      .stButton > button, .stDownloadButton > button, .stLinkButton > a {
        border-radius: 10px; font-weight: 600; border: 1px solid var(--line-2); transition: all .15s; }
      .stButton > button[kind="primary"] { border: 0;
        background: linear-gradient(90deg, var(--accent), var(--accent-2)); color: #0b1020; }
      .stButton > button:hover, .stLinkButton > a:hover { transform: translateY(-1px); border-color: var(--accent); }
      .stTabs [data-baseweb="tab-list"] { gap: .3rem; border-bottom: 1px solid var(--line); }
      .stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: .5rem .9rem; font-weight: 600; }
      input, textarea { border-radius: 10px !important; }

      .job-meta { color: var(--muted); font-size: .92rem; margin-top: -.3rem; }
      .tag { display: inline-block; padding: .18rem .6rem; margin: .15rem .3rem .15rem 0; border-radius: 999px;
             font-size: .76rem; font-weight: 600; border: 1px solid var(--line-2); color: #c7d2fe;
             background: rgba(124,156,255,.08); }
      .tag.good { color: #a7f3d0; border-color: rgba(52,211,153,.35); background: rgba(52,211,153,.08); }
      .tag.dim { color: var(--muted); background: transparent; }
      .score { text-align: center; padding: .55rem .4rem; border-radius: 14px; border: 1px solid; }
      .score b { display: block; font-size: 1.7rem; font-weight: 800; line-height: 1.1; }
      .score small { font-size: .65rem; letter-spacing: .14em; text-transform: uppercase; opacity: .8; }
      .score.high { color: var(--good); border-color: rgba(52,211,153,.4); background: rgba(52,211,153,.08); }
      .score.mid { color: var(--warn); border-color: rgba(251,191,36,.4); background: rgba(251,191,36,.07); }
      .score.low { color: var(--bad); border-color: rgba(248,113,113,.4); background: rgba(248,113,113,.07); }
      .bar { height: 6px; border-radius: 99px; background: var(--line); overflow: hidden; margin: .4rem 0 .7rem; }
      .bar > i { display: block; height: 100%; border-radius: 99px;
                 background: linear-gradient(90deg, var(--accent), var(--accent-2)); }
      .evidence { display: inline-flex; align-items: center; gap: .45rem; font-size: .82rem; font-weight: 600;
                  padding: .3rem .7rem; border-radius: 10px; border: 1px solid; margin: .2rem 0 .4rem; }
      .evidence.strong { color: #a7f3d0; border-color: rgba(52,211,153,.35); background: rgba(52,211,153,.07); }
      .evidence.medium { color: #fde68a; border-color: rgba(251,191,36,.35); background: rgba(251,191,36,.06); }
      .evidence.weak { color: #fecaca; border-color: rgba(248,113,113,.35); background: rgba(248,113,113,.06); }
      .small-note { color: var(--muted); font-size: .83rem; }
      .demo-banner { display: flex; align-items: center; gap: .75rem; padding: .75rem 1rem; margin: .3rem 0 .9rem;
                     border-radius: 14px; border: 1px solid rgba(167,139,250,.35); color: #ddd6fe; font-size: .92rem;
                     background: linear-gradient(90deg, rgba(167,139,250,.14), rgba(124,156,255,.06)); }
      .demo-banner .pill { flex: none; font-size: .68rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase;
                           padding: .22rem .55rem; border-radius: 999px; color: #0b1020; background: var(--accent-2); }
      .feature { padding: 1.1rem 1.2rem; border-radius: 16px; border: 1px solid var(--line);
                 background: rgba(14,20,36,.65); height: 100%; }
      .feature .n { font-family: 'JetBrains Mono', monospace; color: var(--accent); font-size: .8rem; }
      .feature h4 { margin: .3rem 0 .35rem; }
      .feature p { color: var(--muted); font-size: .9rem; margin: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "careerpilot_run" not in st.session_state:
    st.session_state.careerpilot_run = None
st.session_state.setdefault("profile_skills", "Python, FastAPI, PyTorch, RAG, LLMs")
if "careerpilot_error" not in st.session_state:
    st.session_state.careerpilot_error = None

with st.sidebar:
    st.markdown("## 🧭 CareerPilot")
    st.caption("Evidence-driven job intelligence")
    st.divider()
    # Server-side keys are never written into widget values: a password field can be
    # revealed with its eye icon, which would leak the owner's key to every visitor of a
    # deployed app. Typed keys take precedence; otherwise the .env key is used server-side.
    env_key = os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY") or ""
    env_gemini = os.getenv("GEMINI_API_KEY") or ""
    typed_key = st.text_input(
        "SerpApi API key",
        type="password",
        placeholder="Using key from .env" if env_key else "Paste your SerpApi key",
        help="Used in this session for live Google Jobs and Google Search requests. Never stored in the tracker.",
    )
    api_key = typed_key.strip() or env_key
    typed_gemini = st.text_input(
        "Optional Gemini API key",
        type="password",
        placeholder="Using key from .env" if env_gemini else "Optional",
        help="Adds model-assisted query planning. Leave empty for the built-in rule-based planner. Model quota may apply.",
    )
    gemini_key = typed_gemini.strip() or env_gemini
    gemini_model = st.text_input(
        "Gemini model",
        value=os.getenv("GEMINI_MODEL") or "gemini-3.6-flash",
        help="Change this if your Google AI Studio account uses a different supported model.",
    )
    st.markdown("[Get a SerpApi key ↗](https://serpapi.com/) · [Gemini API docs ↗](https://ai.google.dev/gemini-api/docs)")
    st.divider()
    st.markdown("**Agent budget**")
    search_depth = st.slider(
        "Google Jobs query variants",
        min_value=1,
        max_value=3,
        value=2,
        help="Each query can consume a SerpApi search. Exact cached requests may be free under SerpApi's cache policy.",
    )
    pages_per_query = st.slider(
        "Result pages per query",
        min_value=1,
        max_value=3,
        value=1,
        help="Follows SerpApi's next_page_token for more listings. Each extra page is another search.",
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
        "Gemini query planning is optional; the core pipeline works without a model key.</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow"><span class="dot"></span>AI job agent · Powered by SerpApi</div>
      <h1>Find your next role with proof, not noise.</h1>
      <p class="muted" style="max-width:820px;margin-bottom:.15rem;font-size:1.02rem;">
        CareerPilot plans targeted searches, merges duplicate listings, ranks roles against
        your profile, and searches for employer-careers evidence. It reports uncertainty instead
        of pretending a search snippet proves a job is still open.
      </p>
      <div class="hero-steps">
        <span>① Plan queries</span><span>② Search Google Jobs</span><span>③ Merge duplicates</span>
        <span>④ Rank fit</span><span>⑤ Verify evidence</span><span>⑥ Skill-gap insights</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

def _merge_skills(detected: list[str]) -> None:
    """Callback: runs before widgets render, so the skills field can be updated safely."""
    current = [item.strip() for item in st.session_state.get("profile_skills", "").split(",") if item.strip()]
    known = {item.casefold() for item in current}
    st.session_state.profile_skills = ", ".join(current + [item for item in detected if item.casefold() not in known])


# Profile fields are kept in Streamlit session state only; the tracker stores saved job details.
left, right = st.columns([1, 1])
with left:
    role = st.text_input("Target role", value="AI Engineer", key="profile_role")
    location = st.text_input("Preferred location", value="India", key="profile_location")
    work_mode = st.selectbox("Work preference", ["Any", "Remote", "Hybrid", "On-site"], index=0, key="profile_mode")
with right:
    skills_text = st.text_area(
        "Skills to match (comma-separated)",
        height=92,
        key="profile_skills",
    )
    with st.expander("📄 Paste resume text to auto-detect skills"):
        resume_text = st.text_area(
            "Resume text",
            height=140,
            max_chars=20000,
            key="resume_text",
            help="Processed locally against a fixed skill vocabulary. Not sent to SerpApi, Gemini, or stored.",
        )
        detected_skills = extract_skills_from_text(resume_text) if resume_text.strip() else []
        if detected_skills:
            st.caption("Detected: " + md(", ".join(detected_skills)))
            st.button("Add detected skills to profile", on_click=_merge_skills, args=(detected_skills,))
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
                agent = CareerPilotAgent(api_key, gemini_api_key=gemini_key, gemini_model=gemini_model)
                result = agent.run(
                    profile,
                    search_depth=search_depth,
                    verify_top_n=verify_top_n,
                    pages_per_query=pages_per_query,
                )
                result["mode"] = "live"
                result["run_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
                st.session_state.careerpilot_run = result
                st.session_state.careerpilot_error = None
        except Exception as exc:
            st.session_state.careerpilot_error = f"Live search failed: {md(exc)}"

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
        "insights": market_insights(examples, profile),
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
        st.markdown(
            "<div class='demo-banner'><span class='pill'>Demo mode</span>"
            "Every job below is fictional sample data. Add a SerpApi key and run a live search for real results.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.success(
            f"Live SerpApi run complete · {run.get('api_calls', 0)} request(s)"
            f" · {run.get('cache_hits', 0)} cached · {run.get('run_at', '')}"
        )
        st.caption(f"Planner: {md(run.get('planner', 'Built-in rules'))} · model request(s): {run.get('model_calls', 0)}")

    verified_count = sum(
        1 for job in jobs
        if "careers page found" in str(job.get("verification_status", "")).casefold()
        or "corroboration" in str(job.get("verification_status", "")).casefold()
    )
    high_fit_count = sum(1 for job in jobs if int(job.get("score", 0)) >= 75)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Unique roles", len(jobs))
    metric_cols[1].metric("Strong fit (75+)", high_fit_count)
    metric_cols[2].metric("Evidence leads", verified_count if mode == "live" else "—",
                           help="Live mode only: roles with an employer careers page or related corroborating result.")
    metric_cols[3].metric("Search calls", run.get("api_calls", 0) if mode == "live" else 0,
                          help=None if mode == "live" else "Demo mode makes no network requests.")
    if run.get("warnings"):
        with st.expander(f"Search warnings ({len(run['warnings'])})", expanded=False):
            for warning in run["warnings"]:
                st.warning(md(warning))

    tab_discover, tab_insights, tab_tracker, tab_trace, tab_method = st.tabs(
        ["🎯 Discover", "📊 Market insights", "📌 Application tracker", "🧠 Agent trace", "ℹ️ Method & limits"]
    )

    with tab_discover:
        if not jobs:
            st.info("No jobs were returned. Try a broader role title, change the location, or lower the number of cross-checks.")
        else:
            filter_a, filter_b, filter_c = st.columns([2, 2, 2])
            with filter_a:
                min_score = st.slider("Minimum fit score", 0, 100, 0, 5, key="min_fit_score")
            with filter_b:
                sort_by = st.selectbox("Sort by", ["Fit score", "Freshness", "Evidence strength"], key="sort_by")
            with filter_c:
                keyword = st.text_input("Keyword filter", key="keyword_filter", placeholder="e.g. Bengaluru, RAG")
            filtered_jobs = [job for job in jobs if int(job.get("score", 0)) >= min_score]
            if keyword.strip():
                needle = keyword.strip().casefold()
                filtered_jobs = [
                    job for job in filtered_jobs
                    if needle in " ".join(
                        str(job.get(field, "")) for field in ("title", "company", "location", "description")
                    ).casefold()
                ]
            evidence_rank = {
                "likely employer-controlled careers page found": 3,
                "related result found; employer page not confirmed": 2,
            }
            if sort_by == "Freshness":
                filtered_jobs.sort(key=lambda j: int((j.get("score_breakdown") or {}).get("Freshness signal", 0)), reverse=True)
            elif sort_by == "Evidence strength":
                filtered_jobs.sort(
                    key=lambda j: (
                        evidence_rank.get(str(j.get("verification_status", "")).casefold(), 1 if j.get("apply_url") else 0),
                        int(j.get("score", 0)),
                    ),
                    reverse=True,
                )
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
                    row = {column: job.get(column, "") for column in columns}
                    row["matched_skills"] = ", ".join(job.get("matched_skills", []))
                    row["missing_skills"] = ", ".join(job.get("missing_skills", []))
                    writer.writerow({key: csv_safe(value) for key, value in row.items()})
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
                        st.markdown(f"### {index}. {md(job.get('title', 'Untitled role'))}")
                        st.markdown(
                            f"<div class='job-meta'><b>{escape_html(job.get('company', 'Company not listed'))}</b>"
                            f" · {escape_html(job.get('location', 'Location not listed'))}"
                            + (f" · seen in {int(job.get('duplicate_count', 1))} listings"
                               if int(job.get("duplicate_count", 1) or 1) > 1 else "")
                            + "</div>",
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
                            st.caption(" · ".join(md(badge) for badge in badges))
                    with score_col:
                        fit = max(0, min(100, int(job.get("score", 0))))
                        tier = "high" if fit >= 75 else "mid" if fit >= 50 else "low"
                        st.markdown(f"<div class='score {tier}'><b>{fit}%</b><small>fit</small></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='bar'><i style='width:{fit}%'></i></div>", unsafe_allow_html=True)
                    matched = job.get("matched_skills") or []
                    missing = job.get("missing_skills") or []
                    chips = "".join(f"<span class='tag good'>✓ {escape_html(skill)}</span>" for skill in matched[:10])
                    chips += "".join(f"<span class='tag dim'>{escape_html(skill)}</span>" for skill in missing[:8])
                    if chips:
                        st.markdown(chips, unsafe_allow_html=True)
                    if missing:
                        st.caption("Grey skills weren't seen in this listing (not necessarily absent from the actual role).")
                    status = str(job.get("verification_status") or "Not independently checked")
                    lowered = status.casefold()
                    strength = ("strong", "🛡️") if "careers page found" in lowered else (
                        ("medium", "🔗") if "related result" in lowered or "application source" in lowered else ("weak", "⚠️"))
                    st.markdown(
                        f"<div class='evidence {strength[0]}'>{strength[1]} {escape_html(status)}</div>",
                        unsafe_allow_html=True,
                    )
                    description = str(job.get("description") or "")
                    if description:
                        with st.expander("Role details and score explanation"):
                            st.markdown(md(description[:1800] + ("…" if len(description) > 1800 else "")))
                            breakdown = job.get("score_breakdown") or {}
                            if breakdown:
                                st.markdown("**Score components**")
                                for label, value in breakdown.items():
                                    st.markdown(f"- {md(label)}: {int(value)}/100")
                            for reason in job.get("fit_reasons", []):
                                st.markdown(f"- {md(reason)}")
                            st.markdown("**Evidence note**")
                            st.markdown(md(job.get("evidence_snippet") or "No independent source snippet available."))
                            evidence_url = safe_http_url(job.get("evidence_url"))
                            if evidence_url and mode == "live":
                                st.link_button("Open evidence source ↗", evidence_url)
                            if job.get("source_name"):
                                st.caption(f"Search source: {md(job.get('source_name'))}")
                            other_options = [o for o in job.get("apply_options", []) if isinstance(o, dict)][1:6]
                            if other_options and mode == "live":
                                st.markdown("**Other application sources**")
                                for option in other_options:
                                    link = safe_http_url(option.get("link"))
                                    if link:
                                        st.markdown(f"- {md(option.get('title') or 'Source')} — `{md(link)[:120]}`")
                    job_actions = st.columns([1, 1, 4])
                    with job_actions[0]:
                        if st.button("Save to tracker", key=f"save-{index}-{job.get('job_id')}", use_container_width=True):
                            try:
                                save_job(job)
                                st.toast("Saved to application tracker.")
                            except Exception as exc:
                                st.error(f"Could not save job: {exc}")
                    with job_actions[1]:
                        apply_url = safe_http_url(job.get("apply_url"))
                        share_url = safe_http_url(job.get("share_url"))
                        target_url = apply_url or (share_url if mode == "live" else "")
                        if target_url and mode == "live":
                            st.link_button("Open source ↗", target_url, use_container_width=True)
                        elif mode == "demo":
                            st.button("Sample only", key=f"sample-{index}-{job.get('job_id')}", disabled=True, use_container_width=True)
                        else:
                            st.button("No direct link", key=f"nolink-{index}-{job.get('job_id')}", disabled=True, use_container_width=True)

    with tab_insights:
        insights = run.get("insights") or market_insights(jobs, run.get("profile") or profile)
        if not insights.get("total_jobs"):
            st.info("Run a search to see demand signals for this role.")
        else:
            if mode == "demo":
                st.caption("Computed from fictional demo records — illustrative only.")
            ins = st.columns(4)
            ins[0].metric("Average fit", f"{insights['average_fit']}%")
            ins[1].metric("Mention remote", f"{insights['remote_share']}%")
            ins[2].metric("Show salary", f"{insights['salary_share']}%")
            ins[3].metric("Posted ≤ 1 week", f"{insights['fresh_share']}%")
            chart_col, gap_col = st.columns([3, 2])
            with chart_col:
                st.markdown("#### Most-requested skills in these results")
                if insights["top_skills"]:
                    # Green = already in your profile, blue = gap; "-x" sorts the most-requested skill to the top.
                    ranked = insights["top_skills"]
                    st.vega_lite_chart(
                        {
                            "data": {"values": [
                                {"skill": i["skill"], "jobs": i["jobs"],
                                 "status": "In your profile" if i["in_profile"] else "Skill gap"}
                                for i in ranked
                            ]},
                            "mark": {"type": "bar", "cornerRadiusEnd": 4},
                            "encoding": {
                                "y": {"field": "skill", "type": "nominal", "sort": "-x", "title": None},
                                "x": {"field": "jobs", "type": "quantitative", "title": "Listings mentioning skill",
                                      "axis": {"tickMinStep": 1}},
                                "color": {"field": "status", "type": "nominal", "title": None,
                                          "scale": {"domain": ["In your profile", "Skill gap"],
                                                    "range": ["#34d399", "#7c9cff"]},
                                          "legend": {"orient": "bottom"}},
                                "tooltip": [{"field": "skill"}, {"field": "jobs", "title": "Listings"},
                                            {"field": "status"}],
                            },
                        },
                        use_container_width=True,
                    )
                else:
                    st.caption("No known skills were detected in the listing text.")
            with gap_col:
                st.markdown("#### Your skill gaps")
                if insights["skill_gaps"]:
                    for gap in insights["skill_gaps"]:
                        share = next((i["share"] for i in insights["top_skills"] if i["skill"] == gap), 0)
                        st.markdown(f"- **{md(gap)}** — in {share}% of listings")
                    st.caption("Learning or showcasing these could widen your match. Counts reflect only this result set.")
                else:
                    st.success("Your profile already covers the most-requested skills in these results.")
                st.markdown("#### Top hiring companies")
                for item in insights["top_companies"][:6]:
                    st.markdown(f"- {md(item['company'])} · {item['jobs']} listing(s)")

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
                        st.markdown(f"**{md(job.get('title', 'Untitled role'))}**")
                        st.caption(f"{md(job.get('company', 'Unknown company'))} · {md(job.get('location', 'Location not listed'))}")
                        saved_link = safe_http_url(job.get("apply_url"))
                        if job.get("is_demo"):
                            st.caption("DEMO record — fictional sample")
                        elif saved_link:
                            st.link_button("Application source ↗", saved_link)
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
                            try:
                                update_job_status(str(job.get("job_id")), selected_status)
                            except (KeyError, ValueError) as exc:
                                st.error(md(exc))
                            else:
                                st.rerun()
                    with remove_col:
                        st.write("")
                        if st.button("Remove", key=f"remove-{job.get('job_id')}"):
                            remove_saved_job(str(job.get("job_id")))
                            st.rerun()
                    saved_notes = job.get("notes", "")
                    notes_label = "📝 Notes" + (f" · {saved_notes[:60]}{'…' if len(saved_notes) > 60 else ''}" if saved_notes else " · add contacts, follow-ups, interview prep")
                    # Collapsed by default so long trackers stay compact; the preview shows saved notes at a glance.
                    with st.expander(md(notes_label)):
                        # A form keeps the Save button visible; a bare text area only commits on blur.
                        with st.form(key=f"notes-form-{job.get('job_id')}", border=False):
                            notes = st.text_area(
                                "Notes",
                                value=saved_notes,
                                max_chars=2000,
                                height=90,
                                label_visibility="collapsed",
                                placeholder="Recruiter contact, follow-up date, interview prep…",
                            )
                            if st.form_submit_button("Save notes"):
                                update_job_notes(str(job.get("job_id")), notes)
                                st.toast("Notes saved.")
                                st.rerun()
            tracker_csv = io.StringIO()
            tracker_columns = ["title", "company", "location", "status", "saved_at", "score", "apply_url", "notes"]
            tracker_writer = csv.DictWriter(tracker_csv, fieldnames=tracker_columns, extrasaction="ignore")
            tracker_writer.writeheader()
            for job in saved:
                tracker_writer.writerow({c: csv_safe(job.get(c, "")) for c in tracker_columns})
            st.download_button(
                "⬇️ Export tracker as CSV",
                data=tracker_csv.getvalue(),
                file_name="careerpilot_tracker.csv",
                mime="text/csv",
            )

    with tab_trace:
        st.markdown("### What the agent did")
        st.caption("The trace makes the search plan and evidence decisions reviewable.")
        for event in run.get("trace", []):
            st.markdown("• " + md(event))
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
    for col, (num, title, text) in zip((info_a, info_b, info_c), (
        ("01", "Discover", "Live structured job results from SerpApi Google Jobs, merged across queries and pages."),
        ("02", "Investigate", "Google Search cross-checks for employer-careers evidence, with the source link kept."),
        ("03", "Act", "See your skill gaps, save roles, track applications with notes, and export a shortlist."),
    )):
        col.markdown(
            f"<div class='feature'><div class='n'>{num}</div><h4>{title}</h4><p>{text}</p></div>",
            unsafe_allow_html=True,
        )
    st.info("Start a live search with a SerpApi key, or explore the clearly labelled synthetic demo workspace first.")
