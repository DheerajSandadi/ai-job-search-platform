from __future__ import annotations
from datetime import datetime
from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    run_id: str
    started_at: datetime
    current_step: str
    errors: list[str]

    # Job scouting
    raw_jobs: list[dict[str, Any]]
    scored_jobs: list[dict[str, Any]]

    # Approval flow
    approved_jobs: list[dict[str, Any]]
    pending_approvals: list[dict[str, Any]]

    # Resume tailoring
    tailored_resumes: list[dict[str, Any]]

    # Application tracking
    submitted_applications: list[dict[str, Any]]
    failed_applications: list[dict[str, Any]]

    # Recruiter outreach
    recruiters: list[dict[str, Any]]
    outreach_queue: list[dict[str, Any]]
    outreach_sent: list[dict[str, Any]]

    # Summary
    daily_stats: dict[str, int]
