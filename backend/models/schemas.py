from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    DISCOVERED = "discovered"
    SCORED = "scored"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    SUBMITTED = "submitted"
    FAILED = "failed"


class OutreachStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    REPLIED = "replied"
    BOUNCED = "bounced"
    OPT_OUT = "opt_out"


class OutreachChannel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"


class EmailClassification(str, Enum):
    RECRUITER_REPLY = "recruiter_reply"
    INTERVIEW_INVITE = "interview_invite"
    REJECTION = "rejection"
    OFFER = "offer"
    FOLLOW_UP_NEEDED = "follow_up_needed"
    UNRELATED = "unrelated"


class PipelineType(str, Enum):
    MORNING = "morning"
    INBOX = "inbox"
    RETRY = "retry"


class PipelineRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    IDLE = "idle"


# ─── Job ──────────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    title: str
    company: str
    location: str | None = None
    url: str | None = None
    description: str | None = None
    source: str | None = None
    ats_score: float | None = None
    relevance_score: float | None = None
    composite_score: float | None = None
    status: JobStatus = JobStatus.DISCOVERED
    raw_data: dict[str, Any] = Field(default_factory=dict)


class JobUpdate(BaseModel):
    title: str | None = None
    status: JobStatus | None = None
    ats_score: float | None = None
    relevance_score: float | None = None
    composite_score: float | None = None


class Job(JobCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Resume ───────────────────────────────────────────────────────────────────

class ResumeCreate(BaseModel):
    job_id: UUID
    original_text: str
    tailored_text: str
    diff_summary: str | None = None
    ats_score: float | None = None
    keywords_added: list[str] = Field(default_factory=list)


class Resume(ResumeCreate):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Application ──────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    job_id: UUID
    resume_id: UUID | None = None
    status: ApplicationStatus = ApplicationStatus.PENDING
    cover_letter: str | None = None
    applied_at: datetime | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    notes: str | None = None


class Application(ApplicationCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    job: Job | None = None
    resume: Resume | None = None

    model_config = {"from_attributes": True}


# ─── Recruiter ────────────────────────────────────────────────────────────────

class RecruiterCreate(BaseModel):
    name: str
    email: str | None = None
    linkedin_url: str | None = None
    company: str | None = None
    title: str | None = None
    source: str | None = None


class Recruiter(RecruiterCreate):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Outreach ─────────────────────────────────────────────────────────────────

class OutreachCreate(BaseModel):
    recruiter_id: UUID
    job_id: UUID | None = None
    channel: OutreachChannel = OutreachChannel.EMAIL
    subject: str | None = None
    body: str
    status: OutreachStatus = OutreachStatus.QUEUED
    scheduled_at: datetime | None = None


class Outreach(OutreachCreate):
    id: UUID
    sent_at: datetime | None = None
    replied_at: datetime | None = None
    created_at: datetime
    recruiter: Recruiter | None = None

    model_config = {"from_attributes": True}


# ─── Inbox ────────────────────────────────────────────────────────────────────

class InboxEmail(BaseModel):
    id: str
    thread_id: str
    from_address: str
    subject: str
    snippet: str
    body: str | None = None
    received_at: datetime
    classification: EmailClassification | None = None
    draft_reply: str | None = None
    labels: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ─── Analytics ────────────────────────────────────────────────────────────────

class AnalyticsDay(BaseModel):
    date: str
    jobs_discovered: int = 0
    jobs_scored: int = 0
    applications_submitted: int = 0
    applications_failed: int = 0
    recruiters_contacted: int = 0
    recruiter_replies: int = 0
    interviews_scheduled: int = 0

    model_config = {"from_attributes": True}


# ─── Pipeline ─────────────────────────────────────────────────────────────────

class PipelineRun(BaseModel):
    id: UUID | None = None
    pipeline_type: PipelineType
    status: PipelineRunStatus = PipelineRunStatus.IDLE
    started_at: datetime | None = None
    completed_at: datetime | None = None
    stats: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PipelineStatusResponse(BaseModel):
    morning: PipelineRun
    retry: PipelineRun
    inbox: PipelineRun


# ─── Settings ─────────────────────────────────────────────────────────────────

class Settings(BaseModel):
    ats_confidence_threshold: float = 0.8
    morning_pipeline_cron: str = "0 6 * * *"
    retry_pipeline_cron: str = "0 9 * * *"
    auto_apply_enabled: bool = False
    max_applications_per_day: int = 20
    target_roles: list[str] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list)
    anthropic_key_configured: bool = False
    supabase_configured: bool = False
    gmail_configured: bool = False

    model_config = {"from_attributes": True}
