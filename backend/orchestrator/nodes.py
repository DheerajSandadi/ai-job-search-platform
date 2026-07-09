"""LangGraph nodes — one async function per graph node.

Every node:
- wraps agent calls in the module ThreadPoolExecutor (never blocks the loop
  with CrewAI/LLM work),
- catches its own exceptions into ``state["errors"]`` so a single failure
  never kills the run,
- persists results to Supabase via orchestrator.persistence
  (select-then-insert-or-update only — no ``upsert(on_conflict=...)``),
- logs via structlog at start and end.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import structlog

from agents.job_scout.agent import DEFAULT_QUERIES
from agents.job_scout.tools import score_job, search_jobs
from agents.outreach import agent as outreach_agent
from agents.outreach.tools import send_email
from agents.recruiter import agent as recruiter_agent
from agents.resume import agent as resume_agent
from core.config import settings
from core.supabase_client import get_supabase_client
from orchestrator import persistence
from orchestrator.state import PipelineState

logger = structlog.get_logger()

_executor = ThreadPoolExecutor(max_workers=4)  # module-level, reused


async def run_crew_sync(crew_kickoff_fn, *args):
    """Run a synchronous agent call off the event loop (spec §3 pattern)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, crew_kickoff_fn, *args)


def _get_sb():
    return get_supabase_client()


def _score_gate() -> float:
    return settings.ATS_CONFIDENCE_THRESHOLD


def _job_lite(job: dict) -> dict:
    """Trimmed, JSON-safe job payload for checkpointed state (descriptions can
    be tens of KB; keep enough for recruiter search + email drafting)."""
    lite = {k: job.get(k) for k in (
        "title", "company", "location", "url", "source",
        "ats_score", "relevance_score", "composite_score",
    )}
    lite["description"] = (job.get("description") or "")[:500]
    return lite


# ─── discover_jobs ────────────────────────────────────────────────────────────

async def discover_jobs(state: PipelineState) -> PipelineState:
    logger.info("node.discover_jobs.start")
    state["current_step"] = "discover_jobs"
    try:
        raw_jobs = await run_crew_sync(
            lambda: search_jobs(DEFAULT_QUERIES, "Remote", 15)
        )
        state["raw_jobs"] = raw_jobs or []

        if not raw_jobs:
            logger.warning("node.discover_jobs.empty")
            return state

        inserted, skipped = persistence.insert_discovered_jobs(_get_sb(), raw_jobs)
        logger.info("node.discover_jobs.done",
                    total=len(raw_jobs), inserted=inserted, skipped=skipped)

    except Exception as exc:
        logger.error("node.discover_jobs.error", error=str(exc))
        state.setdefault("errors", []).append(f"discover_jobs: {exc}")
        state["raw_jobs"] = []

    return state


# ─── score_jobs ───────────────────────────────────────────────────────────────

async def score_jobs(state: PipelineState) -> PipelineState:
    raw_jobs = state.get("raw_jobs", [])
    gate = _score_gate()
    logger.info("node.score_jobs.start", count=len(raw_jobs), gate=gate)
    state["current_step"] = "score_jobs"

    if not raw_jobs:
        # No new jobs this run — load already-scored jobs from DB so downstream
        # stages (and re-runs) still see them.
        try:
            state["scored_jobs"] = persistence.load_scored_jobs(_get_sb())
            logger.info("node.score_jobs.loaded_from_db", count=len(state["scored_jobs"]))
        except Exception as exc:
            logger.error("node.score_jobs.db_error", error=str(exc))
            state.setdefault("errors", []).append(f"score_jobs: {exc}")
            state["scored_jobs"] = []
    else:
        try:
            scored = await run_crew_sync(lambda: [score_job(j) for j in raw_jobs])
            state["scored_jobs"] = scored or []
            passed = persistence.update_job_scores(_get_sb(), state["scored_jobs"], gate)
            logger.info("node.score_jobs.done",
                        passed=passed, skipped=len(state["scored_jobs"]) - passed)
        except Exception as exc:
            logger.error("node.score_jobs.error", error=str(exc))
            state.setdefault("errors", []).append(f"score_jobs: {exc}")
            state["scored_jobs"] = []

    state["approved_jobs"] = [
        j for j in state.get("scored_jobs", []) if j.get("composite_score", 0.0) >= gate
    ]
    return state


# ─── tailor_resume ────────────────────────────────────────────────────────────

async def tailor_resume(state: PipelineState) -> PipelineState:
    approved = state.get("approved_jobs", [])
    logger.info("node.tailor_resume.start", qualifying=len(approved))
    state["current_step"] = "tailor_resume"
    state["tailored_resumes"] = []
    state["pending_approvals"] = []

    if not approved:
        return state

    sb = _get_sb()
    tailored: list[dict] = []
    pending: list[dict] = []
    run_id = state.get("run_id", "")

    for job in approved:
        try:
            result = await run_crew_sync(lambda j=job: resume_agent.run([j]))
            if not result:
                continue
            resume_data = result[0].get("resume", {})

            entry, is_pending = persistence.save_tailored_application(
                sb, job, _job_lite(job), resume_data, run_id
            )
            if entry is None:
                continue
            tailored.append(entry)
            if is_pending:
                pending.append(entry)
            logger.info("node.tailor_resume.queued",
                        title=job.get("title"), ats_score=resume_data.get("ats_score"))

        except Exception as exc:
            logger.error("node.tailor_resume.error",
                         error=str(exc), job_title=job.get("title"))
            state.setdefault("errors", []).append(
                f"tailor_resume ({job.get('title', '?')}): {exc}")
            continue

    state["tailored_resumes"] = tailored
    state["pending_approvals"] = pending
    logger.info("node.tailor_resume.done", queued=len(pending))
    return state


# ─── await_approval ───────────────────────────────────────────────────────────

async def await_approval(state: PipelineState) -> PipelineState:
    """Checkpoint node — the graph is compiled with
    ``interrupt_after=["await_approval"]`` so execution pauses here until an
    API route feeds a human decision back via ``aupdate_state`` and resumes.
    Deliberately does no work and never polls."""
    logger.info("node.await_approval.pause",
                pending=len(state.get("pending_approvals", [])),
                submitted=len(state.get("submitted_applications", [])))
    state["current_step"] = "await_approval"
    return state


# ─── find_recruiters ──────────────────────────────────────────────────────────

async def find_recruiters(state: PipelineState) -> PipelineState:
    # Recruiter outreach targets jobs the human actually applied to.
    jobs_for_recruiting = state.get("submitted_applications", [])
    logger.info("node.find_recruiters.start", jobs=len(jobs_for_recruiting))
    state["current_step"] = "find_recruiters"
    state["recruiters"] = []
    state["outreach_queue"] = []

    if not jobs_for_recruiting:
        return state

    try:
        batches = await run_crew_sync(
            lambda: recruiter_agent.run(jobs_for_recruiting)
        )
        recruiters, kept = persistence.save_recruiters(_get_sb(), batches or [])
        state["recruiters"] = recruiters
        # Batch structure ({job, recruiters}) is what the outreach agent consumes.
        state["outreach_queue"] = kept
    except Exception as exc:
        logger.error("node.find_recruiters.error", error=str(exc))
        state.setdefault("errors", []).append(f"find_recruiters: {exc}")

    logger.info("node.find_recruiters.done", count=len(state["recruiters"]))
    return state


# ─── generate_outreach ────────────────────────────────────────────────────────

async def generate_outreach(state: PipelineState) -> PipelineState:
    """Draft outreach emails (Sonnet) and persist them as queued outreach rows.
    Sending happens in send_outreach."""
    batches = state.get("outreach_queue", [])
    logger.info("node.generate_outreach.start", batches=len(batches))
    state["current_step"] = "generate_outreach"

    if not batches:
        state["outreach_queue"] = []
        return state

    sb = _get_sb()
    drafted: list[dict] = []

    try:
        records = await run_crew_sync(
            lambda: outreach_agent.run(batches, True)  # dry_run=True: draft only
        )
        for record in (records or []):
            drafted.append({
                "recruiter": record.get("recruiter", {}),
                "job": record.get("job", {}),
                "subject": record.get("subject"),
                "body": record.get("body", ""),
                "outreach_id": persistence.save_outreach_draft(sb, record),
                "sent": False,
            })
    except Exception as exc:
        logger.error("node.generate_outreach.error", error=str(exc))
        state.setdefault("errors", []).append(f"generate_outreach: {exc}")

    state["outreach_queue"] = drafted
    logger.info("node.generate_outreach.done", drafted=len(drafted))
    return state


# ─── send_outreach ────────────────────────────────────────────────────────────

async def send_outreach(state: PipelineState) -> PipelineState:
    queue = state.get("outreach_queue", [])
    logger.info("node.send_outreach.start", queued=len(queue))
    state["current_step"] = "send_outreach"
    sent_records: list[dict] = []

    sb = _get_sb()
    for record in queue:
        to_addr = (record.get("recruiter") or {}).get("email")
        sent = False
        if to_addr:
            try:
                sent = await run_crew_sync(
                    send_email, to_addr, record.get("subject") or "", record.get("body", "")
                )
            except Exception as exc:
                logger.error("node.send_outreach.send_error", to=to_addr, error=str(exc))
                state.setdefault("errors", []).append(f"send_outreach ({to_addr}): {exc}")

        if sent and record.get("outreach_id"):
            persistence.mark_outreach_sent(sb, record["outreach_id"])

        sent_records.append({**record, "sent": sent})

    state["outreach_sent"] = sent_records
    logger.info("node.send_outreach.done",
                sent=len([r for r in sent_records if r["sent"]]))
    return state


# ─── log_skip / log_rejection ─────────────────────────────────────────────────

async def log_skip(state: PipelineState) -> PipelineState:
    """Informational: no job qualified for tailoring this run (not a failure)."""
    gate = _score_gate()
    scored = len(state.get("scored_jobs", []))
    note = f"log_skip: no jobs passed the >={gate} score gate ({scored} scored)"
    logger.info("node.log_skip", scored=scored, gate=gate)
    state.setdefault("errors", []).append(note)
    state["current_step"] = "log_skip"
    return state


async def log_rejection(state: PipelineState) -> PipelineState:
    """Informational: every pending application was rejected by the human."""
    note = "log_rejection: all pending applications were rejected"
    logger.info("node.log_rejection")
    state.setdefault("errors", []).append(note)
    state["current_step"] = "log_rejection"
    return state


# ─── update_analytics ─────────────────────────────────────────────────────────

async def update_analytics(state: PipelineState) -> PipelineState:
    logger.info("node.update_analytics.start")
    today = date.today().isoformat()
    gate = _score_gate()

    scored = state.get("scored_jobs", [])
    newly_sent = len([r for r in state.get("outreach_sent", []) if r.get("sent")])
    analytics_row = {
        "jobs_discovered": len(state.get("raw_jobs", [])),
        "jobs_scored": len([j for j in scored if j.get("composite_score", 0.0) >= gate]),
        "applications_submitted": len(state.get("submitted_applications", [])),
        "applications_failed": len(state.get("failed_applications", [])),
        "recruiters_contacted": newly_sent,
        "recruiter_replies": 0,
        "interviews_scheduled": 0,
    }

    try:
        await run_crew_sync(
            persistence.write_analytics,
            _get_sb(), today, analytics_row,
            bool(state.get("raw_jobs")), newly_sent,
        )
        logger.info("node.update_analytics.saved", **analytics_row)
    except Exception as exc:
        logger.error("node.update_analytics.error", error=str(exc))
        state.setdefault("errors", []).append(f"update_analytics: {exc}")

    state["daily_stats"] = {
        "jobs_found": len(scored),
        "pending_approvals": len(state.get("pending_approvals", [])),
        "applications_sent": analytics_row["applications_submitted"],
        "recruiters_contacted": newly_sent,
        "errors": len(state.get("errors", [])),
    }
    state["current_step"] = "complete"
    logger.info("node.update_analytics.done", **state["daily_stats"])
    return state
