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

        clock = time.monotonic()
        chapters: list[tuple[float, str]] = []

        def chapter(title: str) -> None:
            chapters.append((time.monotonic() - clock, title))

        # 1. Hook
        chapter("1 Hook")
        caption(page, "Job hunting means duplicated, stale, unexplained listings", 5)
        caption(page, "CareerPilot: an AI agent built on live SerpApi data", 5)

        # 2. Sidebar: keys and budget
        chapter("2 Keys and search budget")
        sidebar = page.locator("[data-testid='stSidebar']")
        caption(page, "Keys stay server-side — never shown in the page", 4)
        sidebar.get_by_text("Agent budget").scroll_into_view_if_needed()
        caption(page, "You control the budget: queries, result pages, cross-checks", 6)
        sidebar.get_by_text("CareerPilot").first.scroll_into_view_if_needed()

        # 3. Profile and resume skills
        chapter("3 Profile and resume skills")
        caption(page, "Set a role, location, work mode, experience and skills", 4)
        page.get_by_text("Paste resume text to auto-detect skills").click()
        time.sleep(0.6)
        resume = page.get_by_role("textbox", name="Resume text")
        caption(page, "Or paste a resume — skills are detected locally, nothing is uploaded")
        resume.press_sequentially(RESUME_SNIPPET, delay=12)
        resume.press("Control+Enter")
        settle(page, 1.5)
        page.get_by_role("button", name="Add detected skills to profile").click()
        settle(page, 2.5)

        # 4. Agent run
        chapter("4 Agent run")
        if practice:
            caption(page, "PRACTICE RUN — fictional demo data, not live results")
            page.get_by_role("button", name="Explore demo workspace").click()
        else:
            caption(page, "Plan → search Google Jobs → paginate → merge duplicates → rank → verify")
            page.get_by_role("button", name="Run live agent search").click()
        page.get_by_role("tab", name="Discover").wait_for(timeout=180_000)
        settle(page, 1.5)
        if page.get_by_text("Live search failed").count():
            raise SystemExit("SerpApi returned an error (see the red banner). Fix the key or quota and re-run.")

        # 5. Run summary
        chapter("5 Run summary")
        scroll_to(page, "Unique roles")
        caption(page, "Unique roles, strong fits, evidence leads and exact SerpApi calls", 5)
        caption(page, "Identical searches are cached for 15 minutes to save credits", 4)

        # 6. Job card
        chapter("6 Job card")
        tab(page, "Discover")
        page.locator(".score").first.scroll_into_view_if_needed()
        caption(page, "Every job: colour-coded fit score, matched skills, and an evidence badge", 6)
        caption(page, "Green skills appear in the listing; grey ones weren't mentioned", 4)

        # 7. Score breakdown and sources
        chapter("7 Score breakdown and sources")
        details = page.locator("[data-testid='stExpander']", has_text="Role details and score explanation").first
        details.click()
        time.sleep(0.8)
        details.scroll_into_view_if_needed()
        caption(page, "The score explains itself: role, skills, location, seniority, freshness", 6)
        caption(page, "A ranking aid with sources shown — not a hiring probability", 4)
        details.locator("summary").first.click()
        time.sleep(0.6)

        # 8. Filters and sorting
        chapter("8 Filters and sorting")
        scroll_to(page, "Minimum fit score")
        slider = page.locator(".stSlider", has_text="Minimum fit score").get_by_role("slider")
        caption(page, "Filter by minimum fit score…")
        slider.focus()
        for _ in range(8):
            slider.press("ArrowRight")
            time.sleep(0.12)
        settle(page, 2)
        for _ in range(8):
            slider.press("ArrowLeft")
        settle(page, 0.8)
        caption(page, "…by keyword…")
        keyword = page.get_by_placeholder("e.g. Bengaluru, RAG")
        keyword.press_sequentially("Python", delay=60)
        keyword.press("Enter")
        settle(page, 2)
        keyword.fill("")
        keyword.press("Enter")
        settle(page, 0.8)
        caption(page, "…and sort by evidence strength")
        choose(page, "Sort by", "Evidence strength")
        page.locator(".evidence").first.scroll_into_view_if_needed()
        caption(page, "Employer careers pages first — uncertainty is labelled, never hidden", 5)

        # 9. Export
        chapter("9 Export")
        if page.get_by_role("button", name="⬇️ Export shortlist as CSV").count():
            page.get_by_role("button", name="⬇️ Export shortlist as CSV").scroll_into_view_if_needed()
            caption(page, "Export the shortlist to CSV — formula-safe for Excel", 4)
        else:
            caption(page, "Live runs export the shortlist to CSV (hidden for demo data)", 4)

        # 10. Market insights
        chapter("10 Market insights")
        tab(page, "Market insights")
        caption(page, "Market insights from the live results: fit, remote share, salary, freshness", 5)
        scroll_to(page, "Your skill gaps")
        caption(page, "Green = skills you have · Blue = gaps worth learning next", 6)
        scroll_to(page, "Top hiring companies")
        caption(page, "Plus the companies hiring most for this role", 3)

        # 11. Tracker
        chapter("11 Application tracker")
        tab(page, "Discover")
        page.get_by_role("button", name="Save to tracker").first.click()
        settle(page)
        tab(page, "Application tracker")
        caption(page, "Save roles into a local application tracker", 3)
        choose(page, "Application status", "Applied")
        page.get_by_text("📝 Notes").first.click()
        time.sleep(0.5)
        notes = page.get_by_placeholder("Recruiter contact, follow-up date, interview prep…").first
        caption(page, "Track status and keep notes for each application")
        notes.press_sequentially("Follow up with recruiter on Monday", delay=30)
        page.get_by_role("button", name="Save notes").first.click()
        settle(page, 2)
        scroll_to(page, "Export tracker as CSV")
        caption(page, "Export the tracker any time", 3)

        # 12. Agent trace
        chapter("12 Agent trace")
        tab(page, "Agent trace")
        caption(page, "Full agent trace: every query, page, check and warning is reviewable", 6)

        # 13. Method and limits
        chapter("13 Method and limits")
        tab(page, "Method & limits")
        caption(page, "Scoring weights, evidence labels, data handling and limits — all documented", 5)

        # 14. Close
        chapter("14 Close")
        page.get_by_role("tab", name="Discover").click()
        settle(page, 0.6)
        page.evaluate("window.scrollTo(0, 0)")
        caption(page, "CareerPilot AI — live discovery, verified evidence, explainable ranking, skill-gap insights", 6)
        caption(page, "Also runs headless: python careerpilot.py \"AI Engineer\" --json", 4)
        caption(page, "")
        time.sleep(0.5)
        total = time.monotonic() - clock

        video = page.video
        context.close()
        browser.close()
        source = Path(video.path())
    target = out_dir / ("careerpilot_practice.webm" if practice else "careerpilot_demo.webm")
    shutil.move(str(source), target)
    # Chapter times help line the narration up with the video (the video starts at page load,
    # so these are offset by the first second or two of loading).
    lines = [f"{int(t // 60)}:{int(t % 60):02d}  {title}" for t, title in chapters]
    lines.append(f"{int(total // 60)}:{int(total % 60):02d}  end")
    target.with_suffix(".chapters.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
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
