from __future__ import annotations

from orchestrator.state import PipelineState


def should_tailor(state: PipelineState) -> str:
    """Route to tailor_resumes if there are approved jobs, else skip to find_recruiters."""
    if state.get("approved_jobs"):
        return "tailor_resumes"
    return "find_recruiters"


def should_send_outreach(state: PipelineState) -> str:
    """Route to send_outreach if there are recruiters to contact, else summarize."""
    if state.get("outreach_queue"):
        return "send_outreach"
    return "summarize"
