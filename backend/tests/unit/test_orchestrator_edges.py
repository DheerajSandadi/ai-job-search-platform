"""Unit tests for the LangGraph conditional-edge routers."""
from __future__ import annotations

import pytest

from core.config import settings
from orchestrator.edges import (
    route_after_approval,
    route_after_scoring,
    route_after_tailoring,
)


@pytest.fixture(autouse=True)
def _fixed_gate(monkeypatch):
    monkeypatch.setattr(settings, "ATS_CONFIDENCE_THRESHOLD", 0.8)


# ─── route_after_scoring ──────────────────────────────────────────────────────

def test_scoring_routes_to_tailor_when_job_passes_gate():
    state = {"scored_jobs": [{"composite_score": 0.85}, {"composite_score": 0.4}]}
    assert route_after_scoring(state) == "tailor_resume"


def test_scoring_routes_to_skip_when_all_below_gate():
    state = {"scored_jobs": [{"composite_score": 0.79}], "approved_jobs": []}
    assert route_after_scoring(state) == "log_skip"


def test_scoring_routes_to_skip_when_nothing_scored():
    assert route_after_scoring({"scored_jobs": [], "approved_jobs": []}) == "log_skip"


def test_scoring_gate_is_inclusive():
    state = {"scored_jobs": [{"composite_score": 0.8}]}
    assert route_after_scoring(state) == "tailor_resume"


def test_scoring_respects_prepopulated_approved_jobs():
    state = {"scored_jobs": [], "approved_jobs": [{"title": "x"}]}
    assert route_after_scoring(state) == "tailor_resume"


# ─── route_after_tailoring ────────────────────────────────────────────────────

def test_tailoring_pauses_when_pending_approvals_exist():
    assert route_after_tailoring({"pending_approvals": [{"application_id": "a"}]}) == "await_approval"


def test_tailoring_skips_when_nothing_pending():
    # An empty run must not park at the interrupt forever
    assert route_after_tailoring({"pending_approvals": []}) == "log_skip"


# ─── route_after_approval ─────────────────────────────────────────────────────

def test_approval_routes_to_recruiters_once_applied():
    state = {
        "submitted_applications": [{"application_id": "a"}],
        "pending_approvals": [{"application_id": "b"}],
    }
    assert route_after_approval(state) == "find_recruiters"


def test_approval_routes_to_rejection_when_all_rejected():
    state = {"submitted_applications": [], "pending_approvals": []}
    assert route_after_approval(state) == "log_rejection"


def test_approval_keeps_waiting_while_pending():
    state = {"submitted_applications": [], "pending_approvals": [{"application_id": "a"}]}
    assert route_after_approval(state) == "await_approval"


def test_approval_keeps_waiting_for_approved_but_unapplied():
    # Approve alone doesn't advance the graph — outreach targets applied jobs
    state = {
        "submitted_applications": [],
        "pending_approvals": [{"application_id": "a", "decision": "approved"}],
    }
    assert route_after_approval(state) == "await_approval"
