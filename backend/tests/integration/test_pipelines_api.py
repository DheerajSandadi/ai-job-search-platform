"""Integration tests for /api/v1/pipelines endpoints."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import _mock_sb_table, make_id, now_iso


def _run_row(**kwargs) -> dict:
    return {
        "id": make_id(),
        "pipeline_type": "morning",
        "status": "completed",
        "started_at": now_iso(),
        "completed_at": now_iso(),
        "stats": {},
        "errors": [],
        **kwargs,
    }


# ─── GET /api/v1/pipelines/status ─────────────────────────────────────────────

def test_pipeline_status_returns_three_pipelines(client):
    row = _run_row()
    sb, builder, result = _mock_sb_table([row])

    with patch("api.routes.pipelines.get_supabase_client", return_value=sb):
        resp = client.get("/api/v1/pipelines/status")

    assert resp.status_code == 200
    body = resp.json()
    assert "morning" in body
    assert "inbox" in body
    assert "retry" in body


def test_pipeline_status_returns_idle_when_no_runs(client):
    sb, _, _ = _mock_sb_table([])

    with patch("api.routes.pipelines.get_supabase_client", return_value=sb):
        resp = client.get("/api/v1/pipelines/status")

    assert resp.status_code == 200
    assert resp.json()["morning"]["status"] == "idle"


def test_pipeline_status_503_when_db_unconfigured(client):
    with patch("api.routes.pipelines.get_supabase_client", return_value=None):
        resp = client.get("/api/v1/pipelines/status")
    assert resp.status_code == 503


# ─── POST /api/v1/pipelines/morning/trigger ───────────────────────────────────

def _make_trigger_sb(inserted_row: dict) -> MagicMock:
    """
    Build a Supabase mock for pipeline-trigger tests.
    The running-check select returns [] (no conflict), and insert returns the new row.
    We need separate execute results for select vs insert because they share the same
    fluent builder chain — we use side_effect on execute() to rotate through responses.
    """
    empty_result = MagicMock()
    empty_result.data = []

    insert_result = MagicMock()
    insert_result.data = [inserted_row]

    # First execute() call → empty (running check); second → inserted row
    call_count = {"n": 0}
    responses = [empty_result, insert_result]

    builder = MagicMock()
    def _execute():
        r = responses[min(call_count["n"], len(responses) - 1)]
        call_count["n"] += 1
        return r

    builder.execute.side_effect = _execute
    for method in ("select", "insert", "update", "delete", "upsert",
                   "eq", "neq", "gte", "lte", "lt", "gt", "in_",
                   "not_", "is_", "order", "limit", "range"):
        getattr(builder, method).return_value = builder

    sb = MagicMock()
    sb.table.return_value = builder
    return sb


def test_trigger_morning_pipeline_returns_201_run_row(client):
    inserted_row = _run_row(status="running", pipeline_type="morning")
    sb = _make_trigger_sb(inserted_row)

    with patch("api.routes.pipelines.get_supabase_client", return_value=sb), \
         patch("api.routes.pipelines._execute_pipeline"):
        resp = client.post("/api/v1/pipelines/morning/trigger")

    assert resp.status_code == 200
    body = resp.json()
    assert body["pipeline_type"] == "morning"
    assert body["status"] == "running"


def test_trigger_morning_pipeline_409_when_already_running(client):
    running_row = _run_row(status="running")
    sb, _, _ = _mock_sb_table([running_row])

    with patch("api.routes.pipelines.get_supabase_client", return_value=sb):
        resp = client.post("/api/v1/pipelines/morning/trigger")

    assert resp.status_code == 409


def test_trigger_inbox_pipeline_returns_run_row(client):
    inserted_row = _run_row(status="running", pipeline_type="inbox")
    sb = _make_trigger_sb(inserted_row)

    with patch("api.routes.pipelines.get_supabase_client", return_value=sb), \
         patch("api.routes.pipelines._execute_pipeline"):
        resp = client.post("/api/v1/pipelines/inbox/trigger")

    assert resp.status_code == 200
    assert resp.json()["pipeline_type"] == "inbox"


def test_trigger_retry_pipeline_409_when_already_running(client):
    running_row = _run_row(status="running", pipeline_type="retry")
    sb, _, _ = _mock_sb_table([running_row])

    with patch("api.routes.pipelines.get_supabase_client", return_value=sb):
        resp = client.post("/api/v1/pipelines/retry/trigger")

    assert resp.status_code == 409
