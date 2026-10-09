"""Offline unit tests; these do not consume SerpApi or Gemini quota."""
import os
import tempfile
import unittest
from pathlib import Path

from careerpilot import CareerPilotAgent, deduplicate_jobs, normalize_job, score_job
from storage import VALID_STATUSES, list_saved_jobs, remove_saved_job, save_job, update_job_status


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "role": "AI Engineer",
            "location": "India",
            "work_mode": "Remote",
            "skills": "Python, FastAPI, RAG, PyTorch",
            "experience_years": 0,
        }

    def test_relevant_job_receives_match_reasons(self):
        job = {
            "job_id": "a1",
            "title": "Junior AI Engineer",
            "company": "Example AI",
            "location": "India · Remote",
            "description": "Build Python APIs with FastAPI and RAG retrieval workflows.",
            "posted_at": "2 days ago",
        }
        scored = score_job(job, self.profile)
        self.assertGreaterEqual(scored["score"], 70)
        self.assertIn("Python", scored["matched_skills"])
        self.assertIn("RAG", scored["matched_skills"])
        self.assertIn("Role alignment", scored["score_breakdown"])

    def test_missing_skill_does_not_get_reported_as_matched(self):
        job = {
            "job_id": "a2",
            "title": "Data Analyst",
            "company": "Example Co",
            "location": "London, UK",
            "description": "Build dashboards using SQL and reporting tools.",
            "posted_at": "",
        }
        scored = score_job(job, self.profile)
        self.assertNotIn("PyTorch", scored["matched_skills"])
        self.assertIn("PyTorch", scored["missing_skills"])
        self.assertIn(scored["score"], range(101))

    def test_google_listing_is_not_misrepresented_as_apply_url(self):
        normalized = normalize_job({
            "title": "AI Engineer",
            "company_name": "Example Co",
            "location": "India",
            "link": "https://www.google.com/search?q=example",
        })
        self.assertEqual(normalized["apply_url"], "")
        self.assertEqual(normalized["share_url"], "https://www.google.com/search?q=example")

    def test_deduplication_merges_application_options(self):
        first = {
            "job_id": "one", "title": "AI Engineer", "company": "Example Labs",
            "location": "India", "score": 70, "apply_options": [{"title": "Board A", "link": "https://board.example/a"}],
            "description": "Short description",
        }
        second = {
            "job_id": "two", "title": "AI Engineer", "company": "Example Labs",
            "location": "India", "score": 80, "apply_options": [{"title": "Board B", "link": "https://board.example/b"}],
            "description": "A longer description with extra details.",
        }
        merged = deduplicate_jobs([first, second])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["duplicate_count"], 2)
        self.assertEqual(len(merged[0]["apply_options"]), 2)
        self.assertEqual(merged[0]["score"], 80)

    def test_query_plan_is_distinct_and_bounded(self):
        queries = CareerPilotAgent.build_query_plan(self.profile, depth=3)
        self.assertEqual(len(queries), len(set(queries)))
        self.assertLessEqual(len(queries), 3)
        self.assertTrue(all("AI Engineer" in query for query in queries))


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_db = os.environ.get("CAREERPILOT_DB")
        os.environ["CAREERPILOT_DB"] = str(Path(self.tmp.name) / "tracker.sqlite")

    def tearDown(self):
        if self.previous_db is None:
            os.environ.pop("CAREERPILOT_DB", None)
        else:
            os.environ["CAREERPILOT_DB"] = self.previous_db
        self.tmp.cleanup()

    def test_save_update_remove_lifecycle(self):
        job = {
            "job_id": "tracker-test", "title": "AI Engineer",
            "company": "Example", "location": "India", "score": 82,
        }
        save_job(job)
        saved = list_saved_jobs()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["status"], "Saved")
        update_job_status("tracker-test", "Applied")
        self.assertEqual(list_saved_jobs()[0]["status"], "Applied")
        with self.assertRaises(ValueError):
            update_job_status("tracker-test", "Invented Status")
        self.assertIn("Applied", VALID_STATUSES)
        remove_saved_job("tracker-test")
        self.assertEqual(list_saved_jobs(), [])


if __name__ == "__main__":
    unittest.main()
