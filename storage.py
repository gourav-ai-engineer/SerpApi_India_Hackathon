"""SQLite persistence for CareerPilot's saved jobs and application statuses."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

VALID_STATUSES = ("Saved", "Applied", "Interview", "Offer", "Rejected")


def _db_path() -> Path:
    return Path(os.getenv("CAREERPILOT_DB", "data/careerpilot.db"))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS saved_jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Saved',
            saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            job_json TEXT NOT NULL
        )"""
    )
    connection.commit()
    return connection


def save_job(job: dict[str, Any]) -> None:
    job_id = str(job.get("job_id") or "")
    if not job_id:
        raise ValueError("Cannot save a job without a stable job_id.")
    with _connect() as conn:
        conn.execute(
            """INSERT INTO saved_jobs (job_id, title, company, location, status, job_json)
               VALUES (?, ?, ?, ?, 'Saved', ?)
               ON CONFLICT(job_id) DO UPDATE SET
                 title=excluded.title, company=excluded.company,
                 location=excluded.location, job_json=excluded.job_json""",
            (
                job_id,
                str(job.get("title") or "Untitled role"),
                str(job.get("company") or "Company not listed"),
                str(job.get("location") or "Location not listed"),
                json.dumps(job, ensure_ascii=False, default=str),
            ),
        )


def list_saved_jobs() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT job_id, status, saved_at, job_json FROM saved_jobs ORDER BY saved_at DESC"
        ).fetchall()
    saved: list[dict[str, Any]] = []
    for row in rows:
        try:
            job = json.loads(row["job_json"])
        except (TypeError, json.JSONDecodeError):
            job = {"job_id": row["job_id"], "title": "Saved job", "company": "Unknown"}
        job["job_id"] = row["job_id"]
        job["status"] = row["status"]
        job["saved_at"] = row["saved_at"]
        saved.append(job)
    return saved


def update_job_status(job_id: str, status: str) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(VALID_STATUSES)}")
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE saved_jobs SET status=? WHERE job_id=?",
            (status, str(job_id)),
        )
        if cursor.rowcount == 0:
            raise KeyError("That job is not in the saved-job tracker.")


def remove_saved_job(job_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM saved_jobs WHERE job_id=?", (str(job_id),))
