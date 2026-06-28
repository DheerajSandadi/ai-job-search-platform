"""Shared pytest fixtures for unit and integration tests."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Sample data factories ────────────────────────────────────────────────────

def job_row(**kwargs) -> dict:
    return {
        "id": make_id(),
        "title": "Senior ML Engineer",
        "company": "Acme AI",
        "location": "Remote",
        "url": "https://acme.ai/jobs/123",
        "description": "Build LLM pipelines with Python and LangChain.",
        "source": "indeed",
        "ats_score": 0.82,
        "relevance_score": 0.88,
        "composite_score": 0.86,
        "status": "pending_approval",
        "raw_data": {},
        "created_at": now_iso(),
        "updated_at": now_iso(),
        **kwargs,
    }


def application_row(**kwargs) -> dict:
    jid = make_id()
    return {
        "id": make_id(),
        "job_id": jid,
        "resume_id": make_id(),
        "status": "pending",
        "cover_letter": None,
        "applied_at": None,
        "submitted_at": None,
        "approved_at": None,
        "notes": None,
        "retry_count": 0,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "jobs": job_row(id=jid),
        "resumes": resume_row(job_id=jid),
        **kwargs,
    }


def resume_row(**kwargs) -> dict:
    return {
        "id": make_id(),
        "job_id": kwargs.pop("job_id", make_id()),
        "original_text": "Original resume text.",
        "tailored_text": "Tailored resume text with LangChain keywords.",
        "diff_summary": "Added LangChain, LLM fine-tuning keywords.",
        "ats_score": 0.84,
        "keywords_added": ["LangChain", "LoRA"],
        "created_at": now_iso(),
        **kwargs,
    }


def analytics_row(**kwargs) -> dict:
    return {
        "id": make_id(),
        "date": "2026-06-28",
        "jobs_discovered": 12,
        "jobs_scored": 5,
        "applications_submitted": 3,
        "applications_failed": 0,
        "recruiters_contacted": 2,
        "recruiter_replies": 1,
        "interviews_scheduled": 0,
        **kwargs,
    }


# ─── Mock Supabase builder ────────────────────────────────────────────────────

def _mock_sb_table(rows: list[dict]):
    """Return a fluent mock Supabase client whose .execute() yields `rows`."""
    result = MagicMock()
    result.data = rows

    builder = MagicMock()
    builder.select.return_value = builder
    builder.insert.return_value = builder
    builder.update.return_value = builder
    builder.delete.return_value = builder
    builder.upsert.return_value = builder
    builder.eq.return_value = builder
    builder.neq.return_value = builder
    builder.gte.return_value = builder
    builder.lte.return_value = builder
    builder.lt.return_value = builder
    builder.gt.return_value = builder
    builder.in_.return_value = builder
    builder.not_.return_value = builder
    builder.is_.return_value = builder
    builder.order.return_value = builder
    builder.limit.return_value = builder
    builder.range.return_value = builder
    builder.execute.return_value = result

    sb = MagicMock()
    sb.table.return_value = builder
    return sb, builder, result


# ─── FastAPI TestClient fixture ───────────────────────────────────────────────

@pytest.fixture()
def client():
    """TestClient with scheduler disabled to avoid APScheduler side-effects."""
    with patch("scheduler.jobs.start_scheduler"), patch("scheduler.jobs.stop_scheduler"):
        from main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
