"""Unit tests for the recruiter agent tools."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.recruiter.tools import find_recruiters, rank_recruiters


RECRUITERS = [
    {"name": "Alice Chen",  "title": "Technical Recruiter",    "email": "alice@acme.ai",  "company": "Acme AI"},
    {"name": "Bob Torres",  "title": "Talent Acquisition Lead", "email": "bob@acme.ai",   "company": "Acme AI"},
    {"name": "Carol Wu",    "title": "Engineering Recruiter",   "email": "carol@acme.ai",  "company": "Acme AI"},
]

RANK_RESPONSE = json.dumps({"selected": [0, 2]})


# ─── find_recruiters ─────────────────────────────────────────────────────────

def test_find_recruiters_returns_normalized_list():
    mock_client = MagicMock()
    mock_client.search_recruiters.return_value = [
        {"name": "Alice Chen", "title": "Recruiter", "email": "alice@acme.ai",
         "linkedin_url": None, "company": "Acme AI"}
    ]
    mock_client.normalize.side_effect = lambda r: r  # identity

    with patch("agents.recruiter.tools.get_apollo_client", return_value=mock_client):
        result = find_recruiters("Acme AI", "ML Engineer")

    assert len(result) == 1
    assert result[0]["name"] == "Alice Chen"


def test_find_recruiters_returns_empty_when_none_found():
    mock_client = MagicMock()
    mock_client.search_recruiters.return_value = []

    with patch("agents.recruiter.tools.get_apollo_client", return_value=mock_client):
        result = find_recruiters("Unknown Corp", "ML Engineer")

    assert result == []


# ─── rank_recruiters ─────────────────────────────────────────────────────────

def test_rank_recruiters_selects_subset():
    with patch("agents.recruiter.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = RANK_RESPONSE
        result = rank_recruiters("Acme AI", "ML Engineer", RECRUITERS)

    assert len(result) == 2
    assert result[0]["name"] == "Alice Chen"
    assert result[1]["name"] == "Carol Wu"


def test_rank_recruiters_strips_markdown_fence():
    wrapped = f"```json\n{RANK_RESPONSE}\n```"
    with patch("agents.recruiter.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = wrapped
        result = rank_recruiters("Acme AI", "ML Engineer", RECRUITERS)

    assert len(result) == 2


def test_rank_recruiters_returns_empty_for_empty_input():
    result = rank_recruiters("Acme AI", "ML Engineer", [])
    assert result == []


def test_rank_recruiters_falls_back_to_first_three_on_error():
    with patch("agents.recruiter.tools.anthropic_client") as mock_client:
        mock_client.call_claude.side_effect = RuntimeError("API down")
        result = rank_recruiters("Acme AI", "ML Engineer", RECRUITERS)

    assert len(result) == 3  # fallback returns all (≤3)


def test_rank_recruiters_ignores_out_of_range_indices():
    bad_response = json.dumps({"selected": [0, 99]})  # index 99 doesn't exist
    with patch("agents.recruiter.tools.anthropic_client") as mock_client:
        mock_client.call_claude.return_value = bad_response
        result = rank_recruiters("Acme AI", "ML Engineer", RECRUITERS)

    assert len(result) == 1
    assert result[0]["name"] == "Alice Chen"
