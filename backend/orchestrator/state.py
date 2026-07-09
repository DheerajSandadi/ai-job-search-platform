from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    """LangGraph pipeline state. Every value must be JSON-serializable at node
    boundaries — plain dicts/lists only, no Pydantic or agent objects.

    ``total=False`` so interrupt/resume updates can write partial states;
    ``morning_pipeline.run`` always seeds every key.
    """

    run_id: str
    started_at: datetime  # ISO-8601 string at runtime for JSON-safe checkpoints
    current_step: str
    errors: list[str]

    # Job scouting
    raw_jobs: list[dict[str, Any]]
    scored_jobs: list[dict[str, Any]]
    approved_jobs: list[dict[str, Any]]  # jobs that passed the score gate (>= ATS_CONFIDENCE_THRESHOLD)

    # Resume tailoring / human approval
    tailored_resumes: list[dict[str, Any]]
    pending_approvals: list[dict[str, Any]]  # awaiting human approve/reject in the dashboard

    # Application tracking
    submitted_applications: list[dict[str, Any]]  # marked applied by the human
    failed_applications: list[dict[str, Any]]

    # Recruiter outreach
    recruiters: list[dict[str, Any]]
    outreach_queue: list[dict[str, Any]]
    outreach_sent: list[dict[str, Any]]

    # Summary
    daily_stats: dict[str, int]


def initial_state(run_id: str, started_at: str) -> PipelineState:
    """Fully-populated starting state for a new graph run."""
    return {
        "run_id": run_id,
        "started_at": started_at,
        "current_step": "start",
        "errors": [],
        "raw_jobs": [],
        "scored_jobs": [],
        "approved_jobs": [],
        "tailored_resumes": [],
        "pending_approvals": [],
        "submitted_applications": [],
        "failed_applications": [],
        "recruiters": [],
        "outreach_queue": [],
        "outreach_sent": [],
        "daily_stats": {},
    }
