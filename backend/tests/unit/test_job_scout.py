"""Unit tests for the job_scout agent tools."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.job_scout.tools import filter_jobs, score_job


# ─── score_job ────────────────────────────────────────────────────────────────

SCORE_RESPONSE = json.dumps({
    "ats_score": 0.85,
    "relevance_score": 0.90,
    "composite_score": 0.88,
    "reasoning": "Strong match on Python, LangChain, LLM skills.",
})


def _job(**kwargs) -> dict:
    return {
        "title": "ML Engineer",
        "company": "Acme AI",
        "location": "Remote",
        "description": "Build LLM pipelines. Python, LangChain required.",
        **kwargs,
    }


def test_score_job_populates_scores():
    with patch("agents.job_scout.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = SCORE_RESPONSE
        result = score_job(_job())

    assert result["ats_score"] == pytest.approx(0.85)
    assert result["relevance_score"] == pytest.approx(0.90)
    assert result["composite_score"] == pytest.approx(0.88)


def test_score_job_strips_markdown_fence():
    wrapped = f"```json\n{SCORE_RESPONSE}\n```"
    with patch("agents.job_scout.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = wrapped
        result = score_job(_job())

    assert result["composite_score"] == pytest.approx(0.88)


def test_score_job_defaults_on_claude_error():
    with patch("agents.job_scout.tools.anthropic_client") as mock_client:
        mock_client.call_claude.side_effect = RuntimeError("API down")
        result = score_job(_job())

    assert result["ats_score"] == 0.0
    assert result["relevance_score"] == 0.0
    assert result["composite_score"] == 0.0


def test_score_job_defaults_on_bad_json():
    with patch("agents.job_scout.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = "not json at all"
        result = score_job(_job())

    assert result["composite_score"] == 0.0


# ─── filter_jobs ─────────────────────────────────────────────────────────────

def test_filter_jobs_keeps_qualifying():
    jobs = [
        {**_job(), "composite_score": 0.70},
        {**_job(), "composite_score": 0.50},
        {**_job(), "composite_score": 0.65},
    ]
    result = filter_jobs(jobs, min_score=0.65)
    assert len(result) == 2
    assert all(j["composite_score"] >= 0.65 for j in result)


def test_filter_jobs_empty_when_all_below_threshold():
    jobs = [{**_job(), "composite_score": 0.40}]
    assert filter_jobs(jobs, min_score=0.65) == []


def test_filter_jobs_keeps_all_when_threshold_zero():
    jobs = [{**_job(), "composite_score": 0.10}, {**_job(), "composite_score": 0.90}]
    assert len(filter_jobs(jobs, min_score=0.0)) == 2


def test_filter_jobs_missing_score_treated_as_zero():
    jobs = [{"title": "Dev", "company": "X"}]  # no composite_score key
    assert filter_jobs(jobs, min_score=0.65) == []
