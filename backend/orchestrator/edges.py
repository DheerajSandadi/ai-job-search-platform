"""Conditional-edge routers for the LangGraph StateGraph.

Verified against the pinned langgraph==0.1.19 behavior: routers run when the
source node completes AND are re-evaluated by ``aupdate_state`` — so feeding a
human decision into state while the graph is interrupted re-routes the resumed
run correctly.
"""
from __future__ import annotations

from core.config import settings
from orchestrator.state import PipelineState


def route_after_scoring(state: PipelineState) -> str:
    """tailor_resume if any job passed the score gate, else log_skip."""
    gate = settings.ATS_CONFIDENCE_THRESHOLD
    if any(
        j.get("composite_score", 0.0) >= gate
        for j in state.get("scored_jobs", [])
    ) or state.get("approved_jobs"):
        return "tailor_resume"
    return "log_skip"


def route_after_tailoring(state: PipelineState) -> str:
    """Only pause at the human checkpoint when something is actually awaiting
    approval — otherwise an empty run would sit interrupted forever."""
    if state.get("pending_approvals"):
        return "await_approval"
    return "log_skip"


def route_after_approval(state: PipelineState) -> str:
    """Route the resumed run based on the human decisions fed into state.

    - Something was marked applied      -> find_recruiters (outreach targets
      jobs the human actually applied to — see spec §3 data-flow table)
    - Everything pending was rejected   -> log_rejection
    - Anything still undecided/approved -> await_approval (no-op, interrupts
      again; the graph keeps waiting without polling)
    """
    if state.get("submitted_applications"):
        return "find_recruiters"
    if not state.get("pending_approvals"):
        return "log_rejection"
    return "await_approval"
