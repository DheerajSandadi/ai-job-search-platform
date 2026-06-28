"""Integration tests for /api/v1/analytics endpoints."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from tests.conftest import _mock_sb_table, analytics_row


# ─── GET /api/v1/analytics/today ─────────────────────────────────────────────

def test_today_returns_existing_row(client):
    row = analytics_row(date=date.today().isoformat(), jobs_discovered=10)
    sb, _, _ = _mock_sb_table([row])

    with patch("api.routes.analytics.get_supabase_client", return_value=sb):
        resp = client.get("/api/v1/analytics/today")

    assert resp.status_code == 200
    assert resp.json()["jobs_discovered"] == 10


def test_today_returns_zero_row_when_no_data(client):
    sb, _, _ = _mock_sb_table([])

    with patch("api.routes.analytics.get_supabase_client", return_value=sb):
        resp = client.get("/api/v1/analytics/today")

    assert resp.status_code == 200
    body = resp.json()
    assert body["jobs_discovered"] == 0
    assert body["applications_submitted"] == 0


def test_today_returns_503_when_db_unconfigured(client):
    with patch("api.routes.analytics.get_supabase_client", return_value=None):
        resp = client.get("/api/v1/analytics/today")
    assert resp.status_code == 503


# ─── GET /api/v1/analytics/history ───────────────────────────────────────────

def test_history_returns_list(client):
    rows = [
        analytics_row(date="2026-06-27", applications_submitted=2),
        analytics_row(date="2026-06-28", applications_submitted=4),
    ]
    sb, _, _ = _mock_sb_table(rows)

    with patch("api.routes.analytics.get_supabase_client", return_value=sb):
        resp = client.get("/api/v1/analytics/history?days=7")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_history_empty_list_when_no_data(client):
    sb, _, _ = _mock_sb_table([])

    with patch("api.routes.analytics.get_supabase_client", return_value=sb):
        resp = client.get("/api/v1/analytics/history?days=7")

    assert resp.status_code == 200
    assert resp.json() == []


def test_history_rejects_invalid_days(client):
    # days must be 1–90
    resp = client.get("/api/v1/analytics/history?days=0")
    assert resp.status_code == 422

    resp2 = client.get("/api/v1/analytics/history?days=91")
    assert resp2.status_code == 422


def test_history_503_when_db_unconfigured(client):
    with patch("api.routes.analytics.get_supabase_client", return_value=None):
        resp = client.get("/api/v1/analytics/history?days=7")
    assert resp.status_code == 503
