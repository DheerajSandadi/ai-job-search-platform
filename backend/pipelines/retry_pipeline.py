import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import structlog

from core.supabase_client import get_supabase_client

logger = structlog.get_logger()


def _requeue_failed_applications(stats: dict) -> None:
    sb = get_supabase_client()
    if sb is None:
        logger.warning("retry_pipeline.skipped", reason="database not configured")
        return

    result = sb.table("applications").select(
        "*, jobs(*), resumes(*)"
    ).eq(
        "status", "failed"
    ).lt(
        "retry_count", 3
    ).order(
        "created_at", desc=False
    ).execute()

    failed_apps = result.data or []
    stats["found"] = len(failed_apps)

    if not failed_apps:
        logger.info("retry_pipeline.nothing_to_retry")
        return

    logger.info("retry_pipeline.found", count=len(failed_apps))

    for app in failed_apps:
        app_id = app["id"]
        job = app.get("jobs") or {}
        retry_count = app.get("retry_count") or 0

        try:
            sb.table("applications").update({
                "retry_count": retry_count + 1,
                "status": "pending",
            }).eq("id", app_id).execute()

            sb.table("jobs").update({
                "status": "approved"
            }).eq("id", app["job_id"]).execute()

            logger.info("retry_pipeline.requeued",
                        app_id=app_id,
                        job=job.get("title"),
                        company=job.get("company"),
                        retry_count=retry_count + 1)

            stats["retried"] += 1

        except Exception as e:
            logger.error("retry_pipeline.app_error", app_id=app_id, error=str(e))
            stats["errors"] += 1
            continue

    maxed_out = sb.table("applications").select(
        "id, jobs(title, company)"
    ).eq(
        "status", "failed"
    ).gte(
        "retry_count", 3
    ).execute()

    if maxed_out.data:
        stats["max_retries_reached"] = len(maxed_out.data)
        for app in maxed_out.data:
            job = app.get("jobs") or {}
            logger.warning("retry_pipeline.max_retries_reached",
                           app_id=app["id"],
                           job=job.get("title"),
                           company=job.get("company"))


async def run() -> dict:
    """
    Retry pipeline — runs at 9AM daily.
    Queries Supabase for failed applications with retry_count < 3.
    Re-queues them as pending for manual re-apply, increments retry_count.

    TODO(orchestration fast-follow): now that the LangGraph StateGraph exists
    (orchestrator/graph.py), extend this pipeline to re-enter the graph for
    previously skipped/failed runs instead of only flipping Supabase statuses:
      1. select pipeline_runs where stats->paused_for_approval is absent and
         jobs stayed below the score gate (log_skip path), or applications
         with status='failed';
      2. for each, seed a fresh thread via
         graph.aupdate_state({"configurable": {"thread_id": f"retry:{run_id}"}},
                             seed_state, as_node="score_jobs")
         so routing re-evaluates from scoring (the seeding-at-a-node pattern
         is verified against langgraph==0.1.19 in
         tests/integration/test_orchestration_graph.py);
      3. ainvoke(None, config) to run the tail of the graph.
    Re-queued applications keep working through the manual-approval flow in
    the meantime, so this stub stays behavior-compatible.
    """
    run_id = str(uuid4())
    started_at = datetime.now(timezone.utc)
    logger.info("retry_pipeline.start", run_id=run_id)

    stats = {
        "found": 0,
        "retried": 0,
        "max_retries_reached": 0,
        "errors": 0,
    }
    errors: list[str] = []

    try:
        # Supabase calls are blocking — keep them off the event loop.
        await asyncio.to_thread(_requeue_failed_applications, stats)
        logger.info("retry_pipeline.complete", **stats)
        status = "completed"
    except Exception as e:
        logger.error("retry_pipeline.error", error=str(e))
        stats["errors"] += 1
        errors.append(str(e))
        status = "failed"

    # Same shape as morning/inbox pipelines — pipelines._execute_pipeline
    # reads result["stats"] and result["errors"] when saving the run row.
    return {
        "run_id": run_id,
        "status": status,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "errors": errors,
    }
