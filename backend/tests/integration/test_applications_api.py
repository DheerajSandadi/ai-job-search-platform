"""Integration tests for /api/v1/applications endpoints."""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from tests.conftest import _mock_sb_table, analytics_row, application_row, make_id


# ─── GET /api/v1/applications ─────────────────────────────────────────────────

def test_list_applications_returns_200(client):
    rows = [application_row(), application_row(status="approved")]
    sb, _, _ = _mock_sb_table(rows)

    with patch("api.routes.applications.get_supabase_client", return_value=sb):
        resp = client.get("/api/v1/applications")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_applications_503_when_db_unconfigured(client):
    with patch("api.routes.applications.get_supabase_client", return_value=None):
        resp = client.get("/api/v1/applications")
    assert resp.status_code == 503


# ─── GET /api/v1/applications/pending ────────────────────────────────────────

def test_list_pending_returns_only_pending(client):
    rows = [application_row(status="pending")]
    sb, _, _ = _mock_sb_table(rows)

    with patch("api.routes.applications.get_supabase_client", return_value=sb):
        resp = client.get("/api/v1/applications/pending")

    assert resp.status_code == 200
    assert all(a["status"] == "pending" for a in resp.json())


# ─── POST /api/v1/applications/{id}/approve ───────────────────────────────────

def test_approve_application_returns_200_with_job_url(client):
    app = application_row(status="pending")
    sb, builder, _ = _mock_sb_table([app])

    with patch("api.routes.applications.get_supabase_client", return_value=sb):
        resp = client.post(f"/api/v1/applications/{app['id']}/approve")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == app["id"]
    assert body["job_url"] == app["jobs"]["url"]


def test_approve_application_404_when_not_found(client):
    sb, _, _ = _mock_sb_table([])

    with patch("api.routes.applications.get_supabase_client", return_value=sb):
        resp = client.post(f"/api/v1/applications/{make_id()}/approve")

    assert resp.status_code == 404


def test_approve_application_updates_status_and_job(client):
    app = application_row(status="pending")
    sb, builder, _ = _mock_sb_table([app])
    update_calls: list = []

    def capture_update(payload):
        update_calls.append(payload)
        return builder

    builder.update.side_effect = capture_update

    with patch("api.routes.applications.get_supabase_client", return_value=sb):
        client.post(f"/api/v1/applications/{app['id']}/approve")

    statuses = [c.get("status") for c in update_calls if isinstance(c, dict)]
    assert "approved" in statuses


# ─── POST /api/v1/applications/{id}/reject ────────────────────────────────────

def test_reject_application_returns_200(client):
    app = application_row(status="pending")
    sb, _, _ = _mock_sb_table([app])

    with patch("api.routes.applications.get_supabase_client", return_value=sb):
        resp = client.post(f"/api/v1/applications/{app['id']}/reject")

    assert resp.status_code == 200
    assert resp.json()["id"] == app["id"]


def test_reject_application_404_when_not_found(client):
    sb, _, _ = _mock_sb_table([])

    with patch("api.routes.applications.get_supabase_client", return_value=sb):
        resp = client.post(f"/api/v1/applications/{make_id()}/reject")

    assert resp.status_code == 404


# ─── POST /api/v1/applications/{id}/mark-applied ──────────────────────────────

def test_mark_applied_returns_200_with_timestamp(client):
    app = application_row(status="approved")
    analytics = analytics_row()
    sb, builder, _ = _mock_sb_table([app])

    # Analytics lookup returns a row (so increment path is taken)
    analytics_result = MagicMock()
    analytics_result.data = [analytics]

    def table_dispatch(name: str):
        if name == "analytics":
            b = MagicMock()
            b.select.return_value = b
            b.eq.return_value = b
            b.update.return_value = b
            b.execute.return_value = analytics_result
            return b
        return builder

    sb.table.side_effect = table_dispatch

    with patch("api.routes.applications.get_supabase_client", return_value=sb):
        resp = client.post(f"/api/v1/applications/{app['id']}/mark-applied")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == app["id"]
    assert "applied_at" in body


def test_mark_applied_increments_analytics(client):
    app = application_row(status="approved")
    analytics = analytics_row(applications_submitted=5)
    sb, builder, _ = _mock_sb_table([app])

    captured_analytics_updates: list[dict] = []

    analytics_builder = MagicMock()
    analytics_builder.select.return_value = analytics_builder
    analytics_builder.eq.return_value = analytics_builder
    analytics_builder.update.side_effect = lambda p: (captured_analytics_updates.append(p), analytics_builder)[1]
    analytics_result = MagicMock()
    analytics_result.data = [analytics]
    analytics_builder.execute.return_value = analytics_result

    def table_dispatch(name: str):
        return analytics_builder if name == "analytics" else builder

    sb.table.side_effect = table_dispatch

    with patch("api.routes.applications.get_supabase_client", return_value=sb):
        client.post(f"/api/v1/applications/{app['id']}/mark-applied")

    # Verify the analytics update was called with submitted = previous + 1
    assert any(
        u.get("applications_submitted") == 6
        for u in captured_analytics_updates
    )


def test_mark_applied_404_when_not_found(client):
    sb, _, _ = _mock_sb_table([])

    with patch("api.routes.applications.get_supabase_client", return_value=sb):
        resp = client.post(f"/api/v1/applications/{make_id()}/mark-applied")

    assert resp.status_code == 404
