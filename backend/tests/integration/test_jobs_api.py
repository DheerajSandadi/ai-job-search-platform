"""Integration tests for /api/v1/jobs endpoints."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.conftest import _mock_sb_table, job_row, make_id


# ─── GET /api/v1/jobs ─────────────────────────────────────────────────────────

def test_list_jobs_returns_200(client):
    rows = [job_row(), job_row(company="Beta Corp")]
    sb, _, _ = _mock_sb_table(rows)

    with patch("api.routes.jobs.get_supabase_client", return_value=sb):
        resp = client.get("/api/v1/jobs")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["title"] == "Senior ML Engineer"


def test_list_jobs_deduplicates_same_company_title(client):
    # Same company + title twice → should deduplicate to 1
    row = job_row()
    rows = [row, {**row, "id": make_id()}]
    sb, _, _ = _mock_sb_table(rows)

    with patch("api.routes.jobs.get_supabase_client", return_value=sb):
        resp = client.get("/api/v1/jobs")

    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_jobs_returns_503_when_db_unconfigured(client):
    with patch("api.routes.jobs.get_supabase_client", return_value=None):
        resp = client.get("/api/v1/jobs")

    assert resp.status_code == 503


def test_list_jobs_empty_returns_200(client):
    sb, _, _ = _mock_sb_table([])
    with patch("api.routes.jobs.get_supabase_client", return_value=sb):
        resp = client.get("/api/v1/jobs")

    assert resp.status_code == 200
    assert resp.json() == []


# ─── GET /api/v1/jobs/{id} ────────────────────────────────────────────────────

def test_get_job_returns_job(client):
    job = job_row()
    sb, _, _ = _mock_sb_table([job])

    with patch("api.routes.jobs.get_supabase_client", return_value=sb):
        resp = client.get(f"/api/v1/jobs/{job['id']}")

    assert resp.status_code == 200
    assert resp.json()["id"] == job["id"]


def test_get_job_returns_404_when_not_found(client):
    sb, _, _ = _mock_sb_table([])

    with patch("api.routes.jobs.get_supabase_client", return_value=sb):
        resp = client.get(f"/api/v1/jobs/{make_id()}")

    assert resp.status_code == 404


def test_get_job_returns_422_for_invalid_uuid(client):
    resp = client.get("/api/v1/jobs/not-a-uuid")
    assert resp.status_code == 422
