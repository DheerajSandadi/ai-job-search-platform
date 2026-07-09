"""Integration tests for the morning pipeline entrypoint driving the
LangGraph StateGraph (per-node coverage lives in tests/unit/)."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from core.config import settings
from orchestrator.graph import build_graph
from tests.conftest import FakeSupabase


@pytest.fixture()
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ATS_CONFIDENCE_THRESHOLD", 0.8)
    monkeypatch.setattr(settings, "ORCHESTRATOR_REGISTRY_DB",
                        str(tmp_path / "registry.sqlite"))
    sb = FakeSupabase()
    graph = build_graph(MemorySaver())
    patches = [
        patch("pipelines.morning_pipeline.get_graph", return_value=graph),
        patch("pipelines.morning_pipeline.get_supabase_client", return_value=sb),
        patch("orchestrator.nodes._get_sb", return_value=sb),
    ]
    for p in patches:
        p.start()
    yield sb
    for p in patches:
        p.stop()


@pytest.mark.asyncio
async def test_scheduler_run_creates_and_completes_pipeline_row(env):
    """No jobs found → log_skip path → run completes; the pipeline owns and
    finalizes its own pipeline_runs row (6 AM scheduler path)."""
    from pipelines.morning_pipeline import run

    sb = env
    with patch("orchestrator.nodes.search_jobs", return_value=[]):
        result = await run()

    assert result["status"] == "completed"
    rows = sb.store["pipeline_runs"]
    assert len(rows) == 1
    assert rows[0]["pipeline_type"] == "morning"
    assert rows[0]["status"] == "completed"
    assert rows[0]["completed_at"]
    assert result["run_id"] == rows[0]["id"]  # row id doubles as thread_id


@pytest.mark.asyncio
async def test_triggered_run_does_not_duplicate_pipeline_row(env):
    """The API trigger route creates the row itself and passes its id in —
    run() must reuse it as thread_id and leave row updates to the caller."""
    from pipelines.morning_pipeline import run

    sb = env
    existing_id = "11111111-1111-1111-1111-111111111111"
    sb.store["pipeline_runs"] = [
        {"id": existing_id, "pipeline_type": "morning", "status": "running"}
    ]

    with patch("orchestrator.nodes.search_jobs", return_value=[]):
        result = await run(pipeline_run_id=existing_id)

    assert result["run_id"] == existing_id
    assert len(sb.store["pipeline_runs"]) == 1
    # still "running" — the trigger route's _execute_pipeline finalizes it
    assert sb.store["pipeline_runs"][0]["status"] == "running"


@pytest.mark.asyncio
async def test_paused_run_reports_pending_approvals(env):
    """A run that tailored resumes pauses for review but the morning phase
    reports completed, with paused_for_approval surfaced in stats."""
    from pipelines.morning_pipeline import run

    job = {
        "title": "ML Engineer", "company": "Acme AI", "location": "Remote",
        "url": "https://acme.ai/jobs/1", "description": "LLMs", "source": "dice",
        "ats_score": 0.9, "relevance_score": 0.9, "composite_score": 0.9,
    }
    resume = {"original_text": "o", "tailored_text": "t", "diff_summary": "d",
              "ats_score": 0.9, "keywords_added": []}

    with patch("orchestrator.nodes.search_jobs", return_value=[job]), \
         patch("orchestrator.nodes.score_job", side_effect=lambda j: j), \
         patch("orchestrator.nodes.resume_agent.run",
               side_effect=lambda jobs: [{"job": jobs[0], "resume": resume}]):
        result = await run()

    assert result["status"] == "completed"
    assert result["stats"]["paused_for_approval"] is True
    assert result["stats"]["pending_approvals"] == 1


@pytest.mark.asyncio
async def test_graph_failure_marks_run_failed(env):
    from pipelines.morning_pipeline import run

    sb = env
    with patch("pipelines.morning_pipeline.get_graph",
               side_effect=RuntimeError("compile boom")):
        result = await run()

    assert result["status"] == "failed"
    assert "compile boom" in result["errors"][0]
    assert sb.store["pipeline_runs"][0]["status"] == "failed"
