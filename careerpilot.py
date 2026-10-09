"""CareerPilot's SerpApi-powered job discovery, fit scoring, and evidence checks.

This module deliberately distinguishes search evidence from proof that a vacancy is
still open. Search indexes can lag; every result should be checked before applying.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse

import requests

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
GENERIC_COMPANY_WORDS = {
    "inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation",
    "company", "co", "group", "holdings", "technologies", "technology",
    "solutions", "services", "systems", "software", "private", "pvt",
    "india", "global", "international", "labs", "lab", "digital",
}
CAREER_PATH_WORDS = (
    "career", "careers", "jobs", "job", "vacanc", "opening", "position",
    "work-with-us", "join-us", "opportunit", "requisition",
)
ATS_HOSTS = (
    "greenhouse.io", "lever.co", "myworkdayjobs.com", "ashbyhq.com",
    "smartrecruiters.com", "icims.com", "successfactors.com", "jobvite.com",
    "workable.com", "bamboohr.com",
)


def _tokens(value: str) -> set[str]:
    """Tokenize text without external NLP downloads."""
    return {
        token for token in re.findall(r"[a-z0-9+#.]+", str(value).lower())
        if token not in {"and", "or", "the", "for", "with", "of", "to", "in", "a", "an"}
    }


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _as_skills(value: Any) -> list[str]:
    if isinstance(value, str):
        values = re.split(r"[,;\n]", value)
    elif isinstance(value, (tuple, list, set)):
        values = list(value)
    else:
        values = []
    result: list[str] = []
    for item in values:
        skill = _clean(item)
        if skill and skill.casefold() not in {s.casefold() for s in result}:
            result.append(skill)
    return result


def _extension_value(extensions: Any, keyword: str) -> str:
    if not isinstance(extensions, list):
        return ""
    for value in extensions:
        text = _clean(value)
        if keyword in text.lower():
            return text
    return ""


def _valid_http_url(value: Any) -> str:
    url = _clean(value)
    if not url:
        return ""
    parsed = urlparse(url)
    return url if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def normalize_job(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert a SerpApi Google Jobs result into a stable internal job record."""
    title = _clean(raw.get("title")) or "Untitled role"
    company = _clean(raw.get("company_name") or raw.get("company")) or "Company not listed"
    location = _clean(raw.get("location")) or "Location not listed"
    description = _clean(raw.get("description"))
    extensions = raw.get("extensions", [])
    detected = raw.get("detected_extensions") or {}
    if not isinstance(detected, dict):
        detected = {}

    apply_options_raw = raw.get("apply_options") or []
    apply_options: list[dict[str, str]] = []
    for option in apply_options_raw if isinstance(apply_options_raw, list) else []:
        if not isinstance(option, dict):
            continue
        link = _valid_http_url(option.get("link") or option.get("url"))
        if link:
            apply_options.append({
                "title": _clean(option.get("title") or option.get("source")) or "Application source",
                "link": link,
            })

    share_link = _valid_http_url(raw.get("share_link") or raw.get("link"))
    apply_url = apply_options[0]["link"] if apply_options else share_link
    posted_at = _clean(detected.get("posted_at")) or _extension_value(extensions, "ago")
    schedule_type = _clean(detected.get("schedule_type")) or _extension_value(extensions, "time")
    salary = _clean(detected.get("salary")) or _extension_value(extensions, "₹") or _extension_value(extensions, "$")
    job_id = _clean(raw.get("job_id"))
    if not job_id:
        signature = "|".join((title.casefold(), company.casefold(), location.casefold(), apply_url))
        job_id = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:16]

    return {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "posted_at": posted_at,
        "schedule_type": schedule_type,
        "salary": salary,
        "source_name": _clean(raw.get("via")) or (apply_options[0]["title"] if apply_options else "Google Jobs result"),
        "apply_options": apply_options,
        "apply_url": apply_url,
        "share_url": share_link,
        "score": 0,
        "score_breakdown": {},
        "matched_skills": [],
        "missing_skills": [],
        "fit_reasons": [],
        "verification_status": "Not independently checked",
        "evidence_label": "",
        "evidence_url": "",
        "evidence_snippet": "",
        "is_demo": False,
    }


def _skill_present(skill: str, content: str) -> bool:
    needle = skill.strip().casefold()
    if not needle:
        return False
    if len(needle) <= 3 and re.fullmatch(r"[a-z0-9+#.]+", needle):
        return re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", content) is not None
    return needle in content


def _freshness_score(posted_at: str) -> int:
    value = posted_at.casefold()
    if any(word in value for word in ("just posted", "today", "hour ago", "hours ago", "minute ago", "minutes ago", "yesterday")):
        if "yesterday" in value:
            return 88
        return 100
    match = re.search(r"(\d+)\s+(day|week|month|year)s?\s+ago", value)
    if not match:
        return 45  # Unknown age is not the same as recent.
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "day":
        return 95 if amount <= 3 else 85 if amount <= 7 else 65 if amount <= 30 else 45
    if unit == "week":
        return 70 if amount <= 2 else 55 if amount <= 6 else 35
    if unit == "month":
        return 40 if amount <= 3 else 25
    return 10


def score_job(job: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Add an explainable 0–100 fit score; it is a ranking aid, not a hiring prediction."""
    role = _clean(profile.get("role") or profile.get("job_title"))
    location_requested = _clean(profile.get("location") or "Anywhere")
    work_mode = _clean(profile.get("work_mode") or "Any").casefold()
    try:
        years = max(0, int(profile.get("experience_years") or 0))
    except (TypeError, ValueError):
        years = 0
    skills = _as_skills(profile.get("skills", []))

    title = _clean(job.get("title"))
    description = _clean(job.get("description"))
    company = _clean(job.get("company") or job.get("company_name"))
    location = _clean(job.get("location"))
    posted_at = _clean(job.get("posted_at"))
    combined = f"{title} {description}".casefold()

    role_tokens = _tokens(role)
    title_tokens = _tokens(title)
    if role_tokens:
        overlap = len(role_tokens & title_tokens) / max(1, len(role_tokens))
        role_score = min(100, round(overlap * 78 + (22 if role.casefold() in title.casefold() else 0)))
    else:
        role_score = 50

    matched = [skill for skill in skills if _skill_present(skill, combined)]
    missing = [skill for skill in skills if skill not in matched]
    skill_score = round(100 * len(matched) / len(skills)) if skills else 55

    place_tokens = _tokens(location_requested)
    job_place_tokens = _tokens(location)
    if not location_requested or location_requested.casefold() in {"any", "anywhere", "global"}:
        geo_score = 80
    elif "remote" in location.casefold() and work_mode in {"any", "remote"}:
        geo_score = 100
    elif place_tokens & job_place_tokens:
        geo_score = 100
    elif "remote" in location.casefold() and location_requested.casefold() in location.casefold():
        geo_score = 100
    else:
        geo_score = 30

    job_text = f"{title} {description} {location}".casefold()
    is_remote = "remote" in job_text or "work from home" in job_text or "distributed" in job_text
    if work_mode == "any":
        mode_score = 80
    elif work_mode == "remote":
        mode_score = 100 if is_remote else 25
    elif work_mode == "hybrid":
        mode_score = 100 if "hybrid" in job_text else (45 if is_remote else 75)
    elif work_mode in {"on-site", "onsite", "on site"}:
        mode_score = 25 if is_remote else (100 if any(w in job_text for w in ("on-site", "onsite", "in office")) else 75)
    else:
        mode_score = 70
    location_score = round(0.7 * geo_score + 0.3 * mode_score)

    seniority_words = ("senior", "staff engineer", "principal", "lead engineer", "director", "manager")
    junior_words = ("intern", "internship", "entry level", "entry-level", "junior", "graduate", "fresher")
    is_senior = any(word in title.casefold() for word in seniority_words)
    is_junior = any(word in title.casefold() for word in junior_words)
    if is_senior and years < 4:
        seniority_score = 25
    elif is_senior and years >= 5:
        seniority_score = 100
    elif is_junior and years <= 2:
        seniority_score = 100
    elif is_junior and years > 5:
        seniority_score = 55
    else:
        seniority_score = 75

    freshness = _freshness_score(posted_at)
    # Weights deliberately favor relevant role + skills; unknown dates receive a neutral score.
    fit = round(0.35 * role_score + 0.38 * skill_score + 0.15 * location_score
                + 0.07 * seniority_score + 0.05 * freshness)

    reasons: list[str] = []
    if role_score >= 70:
        reasons.append("Strong title alignment")
    elif role_score >= 40:
        reasons.append("Partial title alignment")
    if matched:
        reasons.append("Skill matches: " + ", ".join(matched[:6]))
    if location_score >= 80:
        reasons.append("Location/work-mode preference looks compatible")
    if posted_at:
        reasons.append("Posting age reported as: " + posted_at)
    else:
        reasons.append("Posting age not supplied by the search result")

    job.update({
        "company": company or "Company not listed",
        "score": max(0, min(100, fit)),
        "score_breakdown": {
            "Role alignment": role_score,
            "Skill match": skill_score,
            "Location & work mode": location_score,
            "Seniority fit": seniority_score,
            "Freshness signal": freshness,
        },
        "matched_skills": matched,
        "missing_skills": missing,
        "fit_reasons": reasons,
    })
    return job


def deduplicate_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge repeat results across search queries using employer, title, and location."""
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for original in jobs:
        job = dict(original)
        company_key = re.sub(r"[^a-z0-9]+", " ", _clean(job.get("company")).casefold()).strip()
        title_key = re.sub(r"[^a-z0-9]+", " ", _clean(job.get("title")).casefold()).strip()
        location_key = re.sub(r"[^a-z0-9]+", " ", _clean(job.get("location")).casefold()).strip()
        key = (company_key, title_key, location_key)
        if key not in unique:
            unique[key] = job
            unique[key]["duplicate_count"] = 1
            continue
        current = unique[key]
        current["duplicate_count"] = int(current.get("duplicate_count", 1)) + 1
        existing_urls = {
            option.get("link") for option in current.get("apply_options", [])
            if isinstance(option, dict) and option.get("link")
        }
        for option in job.get("apply_options", []):
            if isinstance(option, dict) and option.get("link") not in existing_urls:
                current.setdefault("apply_options", []).append(option)
                existing_urls.add(option.get("link"))
        if not current.get("apply_url") and job.get("apply_url"):
            current["apply_url"] = job["apply_url"]
        if len(_clean(job.get("description"))) > len(_clean(current.get("description"))):
            current["description"] = job.get("description", "")
        if int(job.get("score", 0)) > int(current.get("score", 0)):
            # Keep the strongest ranking explanation while retaining merged application sources.
            old_options = current.get("apply_options", [])
            duplicate_count = current.get("duplicate_count", 1)
            current.update(job)
            current["apply_options"] = old_options
            current["duplicate_count"] = duplicate_count
    return list(unique.values())


def _company_terms(company: str) -> list[str]:
    return [
        token for token in _tokens(company)
        if token not in GENERIC_COMPANY_WORDS and token not in {"ai", "it", "hr"}
    ]


def _is_probable_company_domain(company: str, hostname: str) -> bool:
    host = hostname.casefold().removeprefix("www.")
    terms = _company_terms(company)
    return any(term in host for term in terms)


def _looks_like_careers_page(url: str, title: str, snippet: str) -> bool:
    combined = (url + " " + title + " " + snippet).casefold()
    return any(word in combined for word in CAREER_PATH_WORDS)


class SerpApiClient:
    """Small official HTTP client for SerpApi; no key is written to disk."""

    def __init__(self, api_key: str, timeout: int = 30):
        if not _clean(api_key):
            raise ValueError("A SerpApi API key is required for live search.")
        self.api_key = _clean(api_key)
        self.timeout = timeout
        self.session = requests.Session()

    def _search(self, params: dict[str, Any]) -> dict[str, Any]:
        request_params = dict(params)
        request_params["api_key"] = self.api_key
        try:
            response = self.session.get(SERPAPI_ENDPOINT, params=request_params, timeout=self.timeout)
            try:
                data = response.json()
            except ValueError as exc:
                raise RuntimeError("SerpApi returned a response that was not valid JSON.") from exc
            if response.status_code >= 400:
                detail = _clean(data.get("error") if isinstance(data, dict) else "")
                raise RuntimeError(detail or f"SerpApi request failed with HTTP {response.status_code}.")
            if not isinstance(data, dict):
                raise RuntimeError("SerpApi returned an unexpected response shape.")
            if data.get("error"):
                raise RuntimeError(_clean(data.get("error")))
            return data
        except requests.Timeout as exc:
            raise RuntimeError("SerpApi timed out. Try again with a smaller search depth.") from exc
        except requests.RequestException as exc:
            raise RuntimeError("Could not reach SerpApi. Check the network and try again.") from exc

    def search_jobs(self, query: str, location: str) -> dict[str, Any]:
        params: dict[str, Any] = {"engine": "google_jobs", "q": query, "hl": "en", "gl": "in"}
        if location and location.casefold() not in {"any", "anywhere", "global"}:
            params["location"] = location
        return self._search(params)

    def search_web(self, query: str, location: str = "") -> dict[str, Any]:
        params: dict[str, Any] = {"engine": "google", "q": query, "hl": "en", "gl": "in", "num": 6}
        if location and location.casefold() not in {"any", "anywhere", "global"}:
            params["location"] = location
        return self._search(params)


class CareerPilotAgent:
    """A plan → search → normalize → rank → cross-check → report agent pipeline."""

    def __init__(self, api_key: str):
        self.client = SerpApiClient(api_key)

    @staticmethod
    def build_query_plan(profile: dict[str, Any], depth: int = 2) -> list[str]:
        role = _clean(profile.get("role") or profile.get("job_title")) or "Software Engineer"
        skills = _as_skills(profile.get("skills", []))
        candidates = [role]
        if skills:
            candidates.append(role + " " + " ".join(skills[:2]))
        try:
            years = int(profile.get("experience_years") or 0)
        except (TypeError, ValueError):
            years = 0
        if years <= 2:
            candidates.append(role + " junior entry level graduate")
        else:
            candidates.append(role + " experienced hiring")
        return list(dict.fromkeys(candidates))[: max(1, min(3, int(depth)))]

    @staticmethod
    def _verify(job: dict[str, Any], payload: dict[str, Any]) -> None:
        organic = payload.get("organic_results") or []
        title_tokens = _tokens(job.get("title", ""))
        company = _clean(job.get("company"))
        company_terms = _company_terms(company)
        official: dict[str, Any] | None = None
        corroborating: dict[str, Any] | None = None
        for item in organic if isinstance(organic, list) else []:
            if not isinstance(item, dict):
                continue
            url = _valid_http_url(item.get("link"))
            if not url:
                continue
            title = _clean(item.get("title"))
            snippet = _clean(item.get("snippet"))
            host = urlparse(url).netloc.casefold().removeprefix("www.")
            result_tokens = _tokens(title + " " + snippet)
            role_overlap = len(title_tokens & result_tokens) / max(1, len(title_tokens))
            company_match = _is_probable_company_domain(company, host)
            careers_signal = _looks_like_careers_page(url, title, snippet)
            item_copy = {"url": url, "title": title, "snippet": snippet, "host": host}
            if company_match and careers_signal and official is None:
                official = item_copy
            elif role_overlap >= 0.35 and any(term in result_tokens for term in company_terms) and corroborating is None:
                corroborating = item_copy

        if official:
            job["verification_status"] = "Likely employer-controlled careers page found"
            job["evidence_label"] = official["title"] or official["host"]
            job["evidence_url"] = official["url"]
            job["evidence_snippet"] = official["snippet"]
        elif corroborating:
            job["verification_status"] = "Related result found; employer page not confirmed"
            job["evidence_label"] = corroborating["title"] or corroborating["host"]
            job["evidence_url"] = corroborating["url"]
            job["evidence_snippet"] = corroborating["snippet"]
        elif job.get("apply_url"):
            job["verification_status"] = "Application source surfaced; check status manually"
            job["evidence_label"] = "Google Jobs application option"
            job["evidence_url"] = job["apply_url"]
            job["evidence_snippet"] = "The URL came from the structured Google Jobs result; this does not prove the vacancy is still open."
        else:
            job["verification_status"] = "Needs manual verification"
            job["evidence_label"] = "No independent application evidence found"
            job["evidence_url"] = ""
            job["evidence_snippet"] = "Search results did not provide a source strong enough to label as an employer careers page."

    def run(
        self,
        profile: dict[str, Any],
        search_depth: int = 2,
        verify_top_n: int = 3,
    ) -> dict[str, Any]:
        trace: list[str] = []
        queries = self.build_query_plan(profile, search_depth)
        raw_jobs: list[dict[str, Any]] = []
        warnings: list[str] = []
        api_calls = 0

        trace.append("PLAN: prepared " + str(len(queries)) + " distinct Google Jobs query variant(s).")
        for index, query in enumerate(queries, start=1):
            trace.append(f"SEARCH {index}: Google Jobs query = {query!r}")
            try:
                payload = self.client.search_jobs(query, _clean(profile.get("location")))
                api_calls += 1
                found = payload.get("jobs_results") or []
                if not isinstance(found, list):
                    found = []
                trace.append(f"OBSERVE {index}: received {len(found)} structured result(s).")
                raw_jobs.extend(normalize_job(item) for item in found if isinstance(item, dict))
            except Exception as exc:  # Surface actionable errors without crashing the interface.
                message = _clean(str(exc)) or "Unknown search error"
                warnings.append(message)
                trace.append(f"WARNING {index}: {message}")

        jobs = [score_job(job, profile) for job in deduplicate_jobs(raw_jobs)]
        jobs.sort(key=lambda item: int(item.get("score", 0)), reverse=True)
        trace.append(f"RANK: {len(raw_jobs)} raw result(s) became {len(jobs)} unique job(s).")

        checks = max(0, min(int(verify_top_n), len(jobs), 8))
        for index, job in enumerate(jobs[:checks], start=1):
            query = f'"{job.get("title", "")}" "{job.get("company", "")}" careers jobs'
            trace.append(f"CHECK {index}: looking for a related employer/careers page for {job.get('company')}.")
            try:
                payload = self.client.search_web(query, _clean(profile.get("location")))
                api_calls += 1
                self._verify(job, payload)
                trace.append(f"EVIDENCE {index}: {job.get('verification_status')}.")
            except Exception as exc:
                message = _clean(str(exc)) or "Unknown verification search error"
                job["verification_status"] = "Cross-check failed; manual verification needed"
                job["evidence_label"] = "Independent search could not be completed"
                trace.append(f"WARNING CHECK {index}: {message}")
                warnings.append(message)

        for job in jobs[checks:]:
            if job.get("apply_url"):
                job["verification_status"] = "Application source surfaced; not independently checked"
                job["evidence_label"] = "Google Jobs application option"
                job["evidence_url"] = job.get("apply_url", "")
            else:
                job["verification_status"] = "Not cross-checked — prioritize manual verification"

        trace.append(f"REPORT: prepared {len(jobs)} ranked result(s); made {api_calls} SerpApi request(s).")
        trace.append("GUARDRAIL: search evidence is not proof that a job remains open or that an employer is legitimate.")
        return {
            "jobs": jobs,
            "trace": trace,
            "query_plan": queries,
            "api_calls": api_calls,
            "warnings": warnings,
            "profile": dict(profile),
        }
