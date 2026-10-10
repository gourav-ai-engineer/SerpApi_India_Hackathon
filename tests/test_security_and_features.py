"""Offline tests for output safety, caching, pagination, and insights (no network)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from careerpilot import CareerPilotAgent, SerpApiClient, extract_skills_from_text, market_insights
from llm_agent import propose_search_queries
from safety import csv_safe, escape_html, escape_markdown, is_valid_model_name, safe_http_url
from storage import list_saved_jobs, save_job, update_job_notes


class SafetyTests(unittest.TestCase):
    def test_html_is_escaped(self):
        self.assertEqual(escape_html('<img src=x onerror="a()">'), "&lt;img src=x onerror=&quot;a()&quot;&gt;")

    def test_markdown_link_is_neutralized(self):
        escaped = escape_markdown("[Apply](https://evil.example)")
        self.assertNotIn("](", escaped)

    def test_only_http_urls_pass(self):
        self.assertEqual(safe_http_url("javascript:alert(1)"), "")
        self.assertEqual(safe_http_url("data:text/html,x"), "")
        self.assertEqual(safe_http_url("https://ok.example/a b"), "")
        self.assertEqual(safe_http_url("https://ok.example/jobs"), "https://ok.example/jobs")

    def test_csv_formula_injection_is_blocked(self):
        self.assertEqual(csv_safe('=HYPERLINK("http://x")'), '\'=HYPERLINK("http://x")')
        self.assertEqual(csv_safe("AI Engineer"), "AI Engineer")

    def test_model_name_cannot_alter_url_path(self):
        self.assertTrue(is_valid_model_name("gemini-3.6-flash"))
        self.assertFalse(is_valid_model_name("../../v1/other"))
        self.assertFalse(is_valid_model_name("model?key=x"))
        with self.assertRaises(ValueError):
            propose_search_queries({"role": "AI Engineer"}, "key", model="../evil")


def _fake_response(payload, status=200):
    response = mock.Mock()
    response.status_code = status
    response.json.return_value = payload
    return response


class ClientTests(unittest.TestCase):
    def setUp(self):
        SerpApiClient._cache.clear()

    def test_identical_requests_are_served_from_cache(self):
        client = SerpApiClient("k-cache")
        with mock.patch.object(client.session, "get", return_value=_fake_response({"jobs_results": []})) as get:
            client.search_jobs("AI Engineer", "India")
            client.search_jobs("AI Engineer", "India")
        self.assertEqual(get.call_count, 1)
        self.assertEqual(client.cache_hits, 1)

    def test_cache_is_scoped_per_api_key(self):
        with mock.patch("requests.Session.get", return_value=_fake_response({"jobs_results": []})) as get:
            SerpApiClient("key-a").search_jobs("AI", "India")
            SerpApiClient("key-b").search_jobs("AI", "India")
        self.assertEqual(get.call_count, 2)

    def test_agent_follows_next_page_token(self):
        pages = [
            {"jobs_results": [{"title": "AI Engineer", "company_name": "A", "location": "India"}],
             "serpapi_pagination": {"next_page_token": "tok"}},
            {"jobs_results": [{"title": "ML Engineer", "company_name": "B", "location": "India"}]},
        ]
        agent = CareerPilotAgent("k-pages")
        with mock.patch.object(agent.client.session, "get", side_effect=[_fake_response(p) for p in pages]) as get:
            result = agent.run({"role": "AI Engineer", "location": "India"}, search_depth=1,
                               verify_top_n=0, pages_per_query=2)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args.kwargs["params"]["next_page_token"], "tok")
        self.assertEqual(len(result["jobs"]), 2)
        self.assertEqual(result["api_calls"], 2)
        self.assertIn("insights", result)

    def test_api_error_does_not_crash_run(self):
        agent = CareerPilotAgent("k-error")
        with mock.patch.object(agent.client.session, "get",
                               return_value=_fake_response({"error": "Invalid API key."}, 401)):
            result = agent.run({"role": "AI Engineer"}, search_depth=1, verify_top_n=0)
        self.assertEqual(result["jobs"], [])
        self.assertIn("Invalid API key.", result["warnings"])


class InsightTests(unittest.TestCase):
    def test_resume_skill_extraction(self):
        skills = extract_skills_from_text("Built RAG apps in Python with Docker on AWS; some SQL.")
        for expected in ("Python", "RAG", "Docker", "AWS", "SQL"):
            self.assertIn(expected, skills)
        self.assertNotIn("Go", skills)  # short tokens need word boundaries

    def test_llm_spellings_are_one_skill(self):
        insights = market_insights([{"title": "AI Engineer", "description": "LLM apps"}], {"skills": "LLMs"})
        self.assertEqual(insights["skill_gaps"], [])
        self.assertEqual(extract_skills_from_text("LLM and LLMs"), ["LLMs"])

    def test_market_insights_reports_gaps(self):
        jobs = [
            {"title": "AI Engineer", "description": "Python, Docker, Kubernetes", "company": "A", "score": 80},
            {"title": "AI Engineer", "description": "Python and Kubernetes, remote", "company": "A", "score": 60},
        ]
        insights = market_insights(jobs, {"skills": "Python"})
        self.assertEqual(insights["total_jobs"], 2)
        self.assertIn("Kubernetes", insights["skill_gaps"])
        self.assertNotIn("Python", insights["skill_gaps"])
        self.assertEqual(insights["remote_share"], 50)
        self.assertEqual(insights["top_companies"][0], {"company": "A", "jobs": 2})


class NotesTests(unittest.TestCase):
    def test_notes_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"CAREERPILOT_DB": str(Path(tmp) / "t.db")}):
                save_job({"job_id": "n1", "title": "AI Engineer", "company": "X", "location": "India"})
                update_job_notes("n1", "Follow up Friday")
                self.assertEqual(list_saved_jobs()[0]["notes"], "Follow up Friday")
                with self.assertRaises(KeyError):
                    update_job_notes("missing", "x")


if __name__ == "__main__":
    unittest.main()
