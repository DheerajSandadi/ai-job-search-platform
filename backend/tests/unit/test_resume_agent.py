"""Unit tests for the resume agent tools."""
from __future__ import annotations

import json
from unittest.mock import mock_open, patch

import pytest

from agents.resume.tools import load_base_resume, score_resume, tailor_resume


TAILOR_RESPONSE = json.dumps({
    "tailored_text": "Tailored resume with LangChain and LoRA added.",
    "diff_summary": "Added LangChain, LoRA keywords for ATS.",
    "ats_score": 0.87,
    "keywords_added": ["LangChain", "LoRA"],
})

JOB = {
    "title": "Senior ML Engineer",
    "company": "Acme AI",
    "description": "LangChain, LoRA, Python required.",
}


# ─── load_base_resume ─────────────────────────────────────────────────────────

def test_load_base_resume_reads_file():
    with patch("builtins.open", mock_open(read_data="My resume content")):
        text = load_base_resume()
    assert text == "My resume content"


def test_load_base_resume_falls_back_on_missing_file():
    with patch("builtins.open", side_effect=FileNotFoundError):
        text = load_base_resume()
    assert "Dheeraj Reddy" in text


# ─── tailor_resume ────────────────────────────────────────────────────────────

def test_tailor_resume_returns_structured_result():
    with patch("agents.resume.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = TAILOR_RESPONSE
        result = tailor_resume(JOB, base_resume="Original resume.")

    assert result["tailored_text"] == "Tailored resume with LangChain and LoRA added."
    assert result["ats_score"] == pytest.approx(0.87)
    assert "LangChain" in result["keywords_added"]


def test_tailor_resume_strips_markdown_fence():
    wrapped = f"```json\n{TAILOR_RESPONSE}\n```"
    with patch("agents.resume.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = wrapped
        result = tailor_resume(JOB, base_resume="Original.")

    assert result["ats_score"] == pytest.approx(0.87)


def test_tailor_resume_falls_back_on_claude_error():
    with patch("agents.resume.tools.anthropic_client") as mock_client:
        mock_client.call_claude.side_effect = RuntimeError("API error")
        result = tailor_resume(JOB, base_resume="Original.")

    assert result["ats_score"] == 0.0
    assert result["tailored_text"] == "Original."
    assert "failed" in result["diff_summary"].lower()


def test_tailor_resume_loads_base_when_not_provided():
    with patch("agents.resume.tools.anthropic_client") as mock_client, \
         patch("builtins.open", mock_open(read_data="Base resume")):
        mock_client.call_claude.return_value = TAILOR_RESPONSE
        result = tailor_resume(JOB)

    assert result["ats_score"] == pytest.approx(0.87)


# ─── score_resume ─────────────────────────────────────────────────────────────

def test_score_resume_returns_float():
    with patch("agents.resume.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = json.dumps({"ats_score": 0.91})
        score = score_resume(JOB, "Resume text here.")

    assert score == pytest.approx(0.91)


def test_score_resume_returns_zero_on_error():
    with patch("agents.resume.tools.anthropic_client") as mock_client:
        mock_client.call_claude.side_effect = Exception("Boom")
        score = score_resume(JOB, "Resume text.")

    assert score == 0.0
