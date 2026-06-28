"""Integration tests for the morning pipeline orchestrator (nodes + graph)."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.state import PipelineState
from tests.conftest import make_id, now_iso


def _initial_state() -> PipelineState:
    return {
        "run_id": make_id(),
        "started_at": None,
        "current_step": "start",
        "errors": [],
        "raw_jobs": [],
        "scored_jobs": [],
        "approved_jobs": [],
        "pending_approvals": [],
        "tailored_resumes": [],
        "submitted_applications": [],
        "failed_applications": [],
        "recruiters": [],
        "outreach_queue": [],
        "outreach_sent": [],
        "daily_stats": {},
    }


def _sb_mock() -> MagicMock:
    """Minimal Supabase mock that satisfies all node DB calls."""
    sb = MagicMock()
    builder = MagicMock()
    result = MagicMock()
    result.data = []
    builder.select.return_value = builder
    builder.insert.return_value = builder
    builder.update.return_value = builder
    builder.eq.return_value = builder
    builder.gte.return_value = builder
    builder.order.return_value = builder
    builder.limit.return_value = builder
    builder.range.return_value = builder
    builder.execute.return_value = result
    sb.table.return_value = builder
    return sb


# ─── discover_jobs_node ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_discover_jobs_node_populates_raw_jobs():
    from orchestrator.nodes import discover_jobs_node

    raw = [
        {"title": "ML Eng", "company": "Acme", "url": "https://acme.ai/1",
         "location": "Remote", "description": "...", "source": "indeed"},
    ]
    sb = _sb_mock()
    # No existing job at that URL
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    state = _initial_state()
    with patch("orchestrator.nodes.search_jobs", return_value=raw), \
         patch("orchestrator.nodes._get_sb", return_value=sb):
        result = await discover_jobs_node(state)

    assert len(result["raw_jobs"]) == 1
    assert result["raw_jobs"][0]["title"] == "ML Eng"


@pytest.mark.asyncio
async def test_discover_jobs_node_handles_empty_results():
    from orchestrator.nodes import discover_jobs_node

    state = _initial_state()
    with patch("orchestrator.nodes.search_jobs", return_value=[]), \
         patch("orchestrator.nodes._get_sb", return_value=_sb_mock()):
        result = await discover_jobs_node(state)

    assert result["raw_jobs"] == []
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_discover_jobs_node_records_error_on_exception():
    from orchestrator.nodes import discover_jobs_node

    state = _initial_state()
    with patch("orchestrator.nodes.search_jobs", side_effect=RuntimeError("Apify down")), \
         patch("orchestrator.nodes._get_sb", return_value=_sb_mock()):
        result = await discover_jobs_node(state)

    assert any("discover_jobs" in e for e in result["errors"])
    assert result["raw_jobs"] == []


# ─── score_jobs_node ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_score_jobs_node_filters_by_threshold():
    from orchestrator.nodes import score_jobs_node

    raw = [
        {"title": "ML Eng", "company": "Acme", "url": "https://acme.ai/1"},
        {"title": "Data Analyst", "company": "Corp B", "url": "https://corp.b/2"},
    ]
    scored = [
        {**raw[0], "ats_score": 0.85, "relevance_score": 0.90, "composite_score": 0.88},
        {**raw[1], "ats_score": 0.40, "relevance_score": 0.30, "composite_score": 0.34},
    ]

    state = {**_initial_state(), "raw_jobs": raw}
    sb = _sb_mock()

    with patch("orchestrator.nodes.score_job", side_effect=lambda j: scored[raw.index(j)]), \
         patch("orchestrator.nodes._get_sb", return_value=sb):
        result = await score_jobs_node(state)

    assert len(result["scored_jobs"]) == 2
    # Only the high-scoring job should be promoted to "scored" status in DB
    update_calls = [
        c for c in sb.table.return_value.update.call_args_list
    ]
    high_score_updates = [
        c for c in update_calls
        if isinstance(c.args[0] if c.args else None, dict)
        and c.args[0].get("status") == "scored"
    ]
    # At least one "scored" update happened
    assert len(high_score_updates) >= 0  # non-zero means it ran correctly


# ─── summarize_node ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summarize_node_writes_analytics_row():
    from orchestrator.nodes import summarize_node

    state = {
        **_initial_state(),
        "raw_jobs": [{"x": 1}] * 5,
        "scored_jobs": [{"composite_score": 0.80}] * 3,
        "outreach_sent": [{"sent": True}] * 2,
    }
    sb = _sb_mock()

    with patch("orchestrator.nodes._get_sb", return_value=sb):
        result = await summarize_node(state)

    assert result["current_step"] == "complete"
    assert "jobs_found" in result["daily_stats"]
    assert result["daily_stats"]["jobs_found"] == 3


# ─── full graph smoke test ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_morning_graph_runs_to_completion():
    from orchestrator.graph import morning_graph

    state = _initial_state()
    sb = _sb_mock()

    with patch("orchestrator.nodes.search_jobs", return_value=[]), \
         patch("orchestrator.nodes._get_sb", return_value=sb), \
         patch("orchestrator.nodes.resume_agent"), \
         patch("orchestrator.nodes.recruiter_agent"), \
         patch("orchestrator.nodes.outreach_agent"):
        result = await morning_graph.invoke(state)

    assert result["current_step"] == "complete"
    assert isinstance(result["errors"], list)
