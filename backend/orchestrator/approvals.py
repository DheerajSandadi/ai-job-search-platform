"""Bridge between the approve/reject/mark-applied API routes and paused
LangGraph runs.

Supabase remains the source of truth for application status (the routes update
it first, exactly as before); this module additionally feeds the decision into
the interrupted graph run and resumes it so recruiter outreach happens
graph-driven. Any failure here is logged and swallowed — it must never break
the API response.

Decision handling (spec §5, choices flagged in the PR/summary):
- approved  -> recorded in graph state; the run keeps waiting (recruiter
  outreach only makes sense once the human actually applies).
- rejected  -> removed from pending; the run resumes (ends via log_rejection
  once nothing is left pending).
- applied   -> moved to submitted_applications and the run resumes into
  find_recruiters. If the original run already finished (an earlier
  application in the batch already drove outreach), a lightweight follow-on
  thread is seeded at await_approval so this job still gets outreach.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict

import structlog

from orchestrator import registry
from orchestrator.graph import get_graph

logger = structlog.get_logger()

_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
# Hold references so fire-and-forget resume tasks aren't garbage-collected
_tasks: set[asyncio.Task] = set()

_WAIT_NODE = "await_approval"


def schedule_decision(application_id: str, decision: str, app_row: dict | None = None) -> None:
    """Fire-and-forget graph resume; safe to call from any route handler."""
    task = asyncio.create_task(apply_human_decision(application_id, decision, app_row))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def apply_human_decision(
    application_id: str, decision: str, app_row: dict | None = None
) -> None:
    """Feed a human decision (approved | rejected | applied) into the graph
    run that produced the application, and resume it when that can advance
    the flow."""
    try:
        thread_id = registry.lookup_thread(application_id)
        if not thread_id:
            logger.info("approvals.no_thread", application_id=application_id)
            return

        graph = get_graph()
        config = {"configurable": {"thread_id": thread_id}}

        async with _locks[thread_id]:
            snapshot = await graph.aget_state(config)
            if not snapshot.values:
                logger.warning("approvals.no_checkpoint", thread_id=thread_id)
                return

            if snapshot.next == (_WAIT_NODE,):
                await _resume_paused_run(graph, config, snapshot, application_id, decision)
            elif not snapshot.next:
                await _handle_finished_run(
                    graph, thread_id, snapshot, application_id, decision, app_row
                )
            else:
                # Graph is mid-flight past the checkpoint (e.g. outreach for an
                # earlier decision is still running). Supabase already has the
                # status; a later mark-applied will take the follow-on path.
                logger.warning("approvals.run_busy",
                               thread_id=thread_id, next=list(snapshot.next))
    except Exception as exc:
        logger.error("approvals.decision_failed",
                     application_id=application_id, decision=decision, error=str(exc))


def _pop_entry(pending: list[dict], application_id: str, app_row: dict | None) -> tuple[list[dict], dict]:
    """Remove the application's entry from the pending list, synthesizing one
    from the Supabase row if the checkpoint predates it."""
    remaining = [e for e in pending if e.get("application_id") != application_id]
    entry = next((e for e in pending if e.get("application_id") == application_id), None)
    if entry is None:
        job = (app_row or {}).get("jobs") or {}
        entry = {
            "application_id": application_id,
            "job_id": (app_row or {}).get("job_id"),
            "resume_id": (app_row or {}).get("resume_id"),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "description": (job.get("description") or "")[:500],
        }
    return remaining, entry


async def _resume_paused_run(graph, config, snapshot, application_id: str, decision: str) -> None:
    values = snapshot.values
    pending = values.get("pending_approvals", [])
    remaining, entry = _pop_entry(pending, application_id, None)
    entry = {**entry, "decision": decision}

    if decision == "approved":
        # Keep it pending (still waiting for the actual application); just
        # record the decision. aupdate_state re-evaluates the router, which
        # keeps the run parked at await_approval.
        updated_pending = [
            {**e, "decision": "approved"} if e.get("application_id") == application_id else e
            for e in pending
        ]
        await graph.aupdate_state(config, {"pending_approvals": updated_pending}, as_node=_WAIT_NODE)
        logger.info("approvals.recorded", application_id=application_id, decision=decision)
        return

    update: dict = {"pending_approvals": remaining}
    if decision == "applied":
        update["submitted_applications"] = [*values.get("submitted_applications", []), entry]
    await graph.aupdate_state(config, update, as_node=_WAIT_NODE)
    result = await graph.ainvoke(None, config=config)
    logger.info("approvals.resumed",
                application_id=application_id, decision=decision,
                current_step=(result or {}).get("current_step"))


async def _handle_finished_run(
    graph, thread_id: str, snapshot, application_id: str, decision: str, app_row: dict | None
) -> None:
    if decision != "applied":
        # Nothing for the graph to do — Supabase already reflects the status.
        logger.info("approvals.run_already_finished",
                    application_id=application_id, decision=decision)
        return

    # Follow-on run: the original thread already completed (an earlier
    # application drove outreach), so seed a fresh thread at await_approval
    # with just this application and let the normal edges take it through
    # find_recruiters -> outreach -> update_analytics.
    _, entry = _pop_entry(snapshot.values.get("pending_approvals", []), application_id, app_row)
    entry = {**entry, "decision": "applied"}
    followup_id = f"{thread_id}:applied:{application_id[:8]}"
    config = {"configurable": {"thread_id": followup_id}}

    seed = {
        "run_id": followup_id,
        "current_step": _WAIT_NODE,
        "errors": [],
        "raw_jobs": [],
        "scored_jobs": [],
        "approved_jobs": [],
        "tailored_resumes": [],
        "pending_approvals": [],
        "submitted_applications": [entry],
        "failed_applications": [],
        "recruiters": [],
        "outreach_queue": [],
        "outreach_sent": [],
        "daily_stats": {},
    }
    await graph.aupdate_state(config, seed, as_node=_WAIT_NODE)
    result = await graph.ainvoke(None, config=config)
    logger.info("approvals.followup_completed",
                thread_id=followup_id, application_id=application_id,
                current_step=(result or {}).get("current_step"))
