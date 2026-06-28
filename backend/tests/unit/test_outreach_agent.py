"""Unit tests for the outreach agent tools (draft_email + send_email)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.outreach.tools import draft_email, send_email


RECRUITER = {
    "name": "Jane Smith",
    "title": "Technical Recruiter",
    "email": "jane@acme.ai",
}

JOB = {
    "title": "Senior ML Engineer",
    "company": "Acme AI",
}

DRAFT_RESPONSE = json.dumps({
    "subject": "Senior ML Engineer role at Acme AI",
    "body": "Hi Jane, I'm Dheeraj Reddy. I'd love to discuss the ML Engineer role.",
})


# ─── draft_email ──────────────────────────────────────────────────────────────

def test_draft_email_returns_subject_and_body():
    with patch("agents.outreach.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = DRAFT_RESPONSE
        result = draft_email(RECRUITER, JOB)

    assert result["subject"] == "Senior ML Engineer role at Acme AI"
    assert "Dheeraj" in result["body"]


def test_draft_email_strips_markdown_fence():
    wrapped = f"```json\n{DRAFT_RESPONSE}\n```"
    with patch("agents.outreach.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = wrapped
        result = draft_email(RECRUITER, JOB)

    assert result["subject"] != ""
    assert result["body"] != ""


def test_draft_email_falls_back_on_claude_error():
    with patch("agents.outreach.tools.anthropic_client") as mock_client:
        mock_client.call_claude.side_effect = RuntimeError("API down")
        result = draft_email(RECRUITER, JOB)

    # Should still return a valid structure (fallback)
    assert "subject" in result
    assert "body" in result
    assert result["subject"] != ""


def test_draft_email_uses_recruiter_name_in_fallback():
    with patch("agents.outreach.tools.anthropic_client") as mock_client:
        mock_client.call_claude.side_effect = Exception("Boom")
        result = draft_email(RECRUITER, JOB)

    assert "Jane" in result["body"] or "Jane" in result.get("subject", "")


# ─── send_email ───────────────────────────────────────────────────────────────

def test_send_email_returns_true_on_success():
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {}
    with patch("agents.outreach.tools.get_gmail_service", return_value=mock_service):
        ok = send_email("jane@acme.ai", "Subject", "Body text")

    assert ok is True


def test_send_email_returns_false_when_gmail_not_configured():
    with patch("agents.outreach.tools.get_gmail_service", return_value=None):
        ok = send_email("jane@acme.ai", "Subject", "Body text")

    assert ok is False


def test_send_email_returns_false_on_gmail_api_error():
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = Exception("Gmail error")
    with patch("agents.outreach.tools.get_gmail_service", return_value=mock_service):
        ok = send_email("jane@acme.ai", "Subject", "Body text")

    assert ok is False
