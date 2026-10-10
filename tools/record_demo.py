"""Record a captioned walkthrough of CareerPilot with Playwright.

Start the app first (`streamlit run app.py`), then in a second terminal:

    python -m pip install playwright
    python -m playwright install chromium
    python tools/record_demo.py                # live run: needs SERPAPI_API_KEY in .env
    python tools/record_demo.py --practice     # demo-mode rehearsal, no API calls

The live recording is the one to submit; practice videos use fictional jobs and
are labelled as such. The video is saved to recordings/ as .webm (YouTube accepts
it directly). The script never types or displays the API key: live mode relies on
the key the app reads from .env.
"""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

RESUME_SNIPPET = (
    "Built retrieval-augmented generation (RAG) services in Python with FastAPI, "
    "containerised with Docker, and deployed on AWS. Comfortable with SQL and Git."
)

CAPTION_JS = """
(text) => {
  let el = document.getElementById('cp-caption');
  if (!el) {
    el = document.createElement('div');
    el.id = 'cp-caption';
    Object.assign(el.style, {
      position: 'fixed', left: '50%', bottom: '28px', transform: 'translateX(-50%)',
      zIndex: 999999, maxWidth: '80%', padding: '12px 20px', borderRadius: '14px',
      background: 'rgba(7,11,22,.92)', border: '1px solid #7c9cff', color: '#eef2ff',
      font: '600 20px Inter, system-ui, sans-serif', textAlign: 'center',
      boxShadow: '0 10px 30px rgba(0,0,0,.45)', transition: 'opacity .25s',
    });
    document.body.appendChild(el);
  }
  el.style.opacity = text ? '1' : '0';
  el.textContent = text;
}
"""


def caption(page: Page, text: str, hold: float = 0.0) -> None:
    page.evaluate(CAPTION_JS, text)
    if hold:
        time.sleep(hold)


def settle(page: Page, seconds: float = 1.2) -> None:
    """Wait for Streamlit to finish rerunning, then pause so viewers can follow."""
    try:
        page.wait_for_selector("[data-testid='stStatusWidget']", state="detached", timeout=60_000)
    except Exception:
        pass
    time.sleep(seconds)


def scroll_to(page: Page, text: str) -> None:
    page.get_by_text(text, exact=False).first.scroll_into_view_if_needed()
    time.sleep(0.6)


def choose(page: Page, label: str, option: str) -> None:
    """Pick an option from a Streamlit selectbox identified by its label."""
    box = page.locator(".stSelectbox", has_text=label).first
    box.scroll_into_view_if_needed()
    box.get_by_role("combobox").click()
    page.get_by_role("option", name=option, exact=True).click()
    settle(page)


def tab(page: Page, name: str) -> None:
    page.get_by_role("tab", name=name).click()
    settle(page, 0.8)
    page.get_by_role("tab", name=name).scroll_into_view_if_needed()


def record(url: str, practice: bool, out_dir: Path, headless: bool = False, chromium: str | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=60, executable_path=chromium)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(out_dir),
            record_video_size={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.goto(url)
        page.get_by_text("Run live agent search").wait_for(timeout=60_000)
        settle(page, 1.0)

        # 0:00 — problem
        caption(page, "Job hunting = duplicated, stale, unexplained listings. CareerPilot is an AI agent that fixes that.", 6)
        caption(page, "Live data from SerpApi Google Jobs + Google Search", 4)

        # Resume skill detection
        caption(page, "Paste a resume: skills are detected locally — nothing is sent to any API")
        page.get_by_text("Paste resume text to auto-detect skills").click()
        time.sleep(0.6)
        page.get_by_role("textbox", name="Resume text").fill(RESUME_SNIPPET)
        page.get_by_role("textbox", name="Resume text").press("Control+Enter")
        settle(page)
        page.get_by_role("button", name="Add detected skills to profile").click()
        settle(page, 2)

        # Agent run
        if practice:
            caption(page, "PRACTICE RUN — fictional demo data, not live results")
            page.get_by_role("button", name="Explore demo workspace").click()
        else:
            caption(page, "The agent plans queries, searches Google Jobs, merges duplicates, ranks, and verifies")
            page.get_by_role("button", name="Run live agent search").click()
        page.get_by_role("tab", name="Discover").wait_for(timeout=180_000)
        settle(page, 1.5)
        if page.get_by_text("Live search failed").count():
            raise SystemExit("SerpApi returned an error (see the red banner). Fix the key or quota and re-run.")
        scroll_to(page, "Unique roles")
        caption(page, "Every request is counted; repeat searches are cached to save credits", 4)

        # Ranking
        tab(page, "Discover")
        caption(page, "Explainable fit score: role, skills, location, seniority, freshness", 2)
        page.locator("[data-testid='stExpander']", has_text="Role details and score explanation").first.click()
        time.sleep(0.8)
        page.locator("[data-testid='stExpander']", has_text="Role details and score explanation").first.scroll_into_view_if_needed()
        time.sleep(4)
        caption(page, "It's a ranking aid, not a hiring probability", 2.5)

        # Evidence
        tab(page, "Discover")
        choose(page, "Sort by", "Evidence strength")
        caption(page, "Top results are cross-checked via Google Search for the employer's careers page", 3)
        page.locator(".evidence").first.scroll_into_view_if_needed()
        caption(page, "Evidence is labelled honestly — uncertainty is reported, never hidden", 4)

        # Insights
        tab(page, "Market insights")
        caption(page, "Market insights: what these live listings demand", 2.5)
        scroll_to(page, "Your skill gaps")
        caption(page, "Green = skills you have · Blue = skill gaps worth learning next", 5)

        # Tracker
        tab(page, "Discover")
        page.get_by_role("button", name="Save to tracker").first.click()
        settle(page)
        tab(page, "Application tracker")
        caption(page, "Save roles, track status, keep notes, export to CSV")
        choose(page, "Application status", "Applied")
        page.get_by_text("📝 Notes").first.click()
        time.sleep(0.5)
        notes = page.get_by_placeholder("Recruiter contact, follow-up date, interview prep…").first
        notes.fill("Follow up with recruiter on Monday")
        page.get_by_role("button", name="Save notes").first.click()
        settle(page, 2.5)

        # Trace + close
        tab(page, "Agent trace")
        caption(page, "Full agent trace: plan → search → pages → rank → check → report", 4)
        caption(page, "CareerPilot AI — live discovery, verified evidence, explainable ranking, skill-gap insights", 5)
        caption(page, "")
        time.sleep(0.5)

        video = page.video
        context.close()
        browser.close()
        source = Path(video.path())
    target = out_dir / ("careerpilot_practice.webm" if practice else "careerpilot_demo.webm")
    shutil.move(str(source), target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8501")
    parser.add_argument("--practice", action="store_true", help="Use demo mode (no SerpApi calls)")
    parser.add_argument("--out", default="recordings")
    parser.add_argument("--headless", action="store_true", help="Record without showing the browser window")
    parser.add_argument("--chromium", default=None, help="Path to a Chromium binary (optional)")
    args = parser.parse_args()
    path = record(args.url, args.practice, Path(args.out), args.headless, args.chromium)
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
