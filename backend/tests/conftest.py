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


# ─── In-memory fake Supabase ─────────────────────────────────────────────────
# The fluent MagicMock above always returns the same rows; graph integration
# tests need real per-table state (insert then select back). This fake
# supports the subset of PostgREST chaining the codebase uses.

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, store: dict, table: str):
        self._store = store
        self._table = table
        self._op = "select"
        self._payload = None
        self._filters: list[tuple[str, object]] = []
        self._limit: int | None = None

    # ops
    def select(self, *_args, **_kwargs):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    # filters / modifiers (only what the app uses)
    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def lt(self, col, val):  # retry pipeline
        return self

    def gte(self, col, val):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, *_args):
        return self

    def _rows(self):
        rows = self._store.setdefault(self._table, [])
        return [r for r in rows if all(str(r.get(c)) == str(v) for c, v in self._filters)]

    def execute(self):
        rows = self._store.setdefault(self._table, [])
        if self._op == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted = []
            for p in payloads:
                row = {"id": make_id(), "created_at": now_iso(), **p}
                rows.append(row)
                inserted.append(row)
            return _FakeResult(inserted)
        if self._op == "update":
            matched = self._rows()
            for r in matched:
                r.update(self._payload)
            return _FakeResult(matched)
        if self._op == "delete":
            matched = self._rows()
            self._store[self._table] = [r for r in rows if r not in matched]
            return _FakeResult(matched)
        matched = self._rows()
        if self._limit is not None:
            matched = matched[: self._limit]
        return _FakeResult(matched)


class FakeSupabase:
    """Minimal in-memory Supabase stand-in. Access rows via .store[table]."""

    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name: str) -> _FakeQuery:
        return _FakeQuery(self.store, name)


# ─── FastAPI TestClient fixture ───────────────────────────────────────────────

@pytest.fixture()
def client():
    """TestClient with scheduler disabled to avoid APScheduler side-effects."""
    with patch("scheduler.jobs.start_scheduler"), patch("scheduler.jobs.stop_scheduler"):
        from main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
