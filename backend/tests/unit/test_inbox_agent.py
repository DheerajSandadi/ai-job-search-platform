"""Unit tests for the inbox agent tools (classify + draft_reply)."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from agents.inbox.tools import classify_email, draft_reply


EMAIL = {
    "id": "msg_001",
    "sender_email": "recruiter@acme.ai",
    "subject": "Interested in your ML background",
    "full_body": "Hi Dheeraj, we have a Senior ML Engineer role that fits your profile.",
    "body_preview": "Hi Dheeraj, we have a Senior ML Engineer role...",
}

CLASSIFY_RESPONSE = json.dumps({
    "classification": "recruiter_reply",
    "confidence": 0.95,
})

REJECTION_RESPONSE = json.dumps({
    "classification": "rejection",
    "confidence": 0.90,
})


# ─── classify_email ───────────────────────────────────────────────────────────

def test_classify_email_returns_classification():
    with patch("agents.inbox.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = CLASSIFY_RESPONSE
        result = classify_email(EMAIL)

    assert result["classification"] == "recruiter_reply"
    assert result["confidence"] == pytest.approx(0.95)


def test_classify_email_strips_markdown_fence():
    wrapped = f"```json\n{CLASSIFY_RESPONSE}\n```"
    with patch("agents.inbox.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = wrapped
        result = classify_email(EMAIL)

    assert result["classification"] == "recruiter_reply"


def test_classify_email_defaults_unrelated_on_error():
    with patch("agents.inbox.tools.anthropic_client") as mock_client:
        mock_client.call_claude.side_effect = RuntimeError("API down")
        result = classify_email(EMAIL)

    assert result["classification"] == "unrelated"
    assert result["confidence"] == 0.0


def test_classify_email_defaults_unrelated_on_bad_json():
    with patch("agents.inbox.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = "garbage"
        result = classify_email(EMAIL)

    assert result["classification"] == "unrelated"


# ─── draft_reply ──────────────────────────────────────────────────────────────

def test_draft_reply_returns_text_for_actionable():
    email_with_clf = {**EMAIL, "classification": "recruiter_reply"}
    with patch("agents.inbox.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = "Thanks for reaching out! I'd love to connect."
        reply = draft_reply(email_with_clf)

    assert reply is not None
    assert "connect" in reply


def test_draft_reply_returns_none_for_unrelated():
    email_with_clf = {**EMAIL, "classification": "unrelated"}
    reply = draft_reply(email_with_clf)
    assert reply is None


def test_draft_reply_returns_none_on_claude_error():
    email_with_clf = {**EMAIL, "classification": "recruiter_reply"}
    with patch("agents.inbox.tools.anthropic_client") as mock_client:
        mock_client.call_claude.side_effect = Exception("Boom")
        reply = draft_reply(email_with_clf)

    assert reply is None
