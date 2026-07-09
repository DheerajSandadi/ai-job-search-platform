from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import structlog

from core.supabase_client import get_supabase_client
from orchestrator.graph import get_graph
from orchestrator.state import initial_state

logger = structlog.get_logger()


async def run(pipeline_run_id: str | None = None) -> dict:
    """Execute the morning pipeline via the LangGraph StateGraph.

    The pipeline_runs row id doubles as the LangGraph thread_id so a paused
    run is traceable back to the dashboard row. When the API trigger route
    already created the row it passes the id in (and owns the final update);
    the 6 AM scheduler calls with no argument, so the row is managed here.
    """
    sb = get_supabase_client()
    started_at = datetime.now(timezone.utc)
    owns_row = pipeline_run_id is None and sb is not None

    run_id = pipeline_run_id
    if run_id is None:
        if sb is not None:
            try:
                inserted = sb.table("pipeline_runs").insert({
                    "pipeline_type": "morning",
                    "status": "running",
                    "started_at": started_at.isoformat(),
                }).execute()
                run_id = inserted.data[0]["id"]
            except Exception as exc:
                logger.error("morning_pipeline.run_row_failed", error=str(exc))
                owns_row = False
        if run_id is None:
            run_id = str(uuid4())

    logger.info("morning_pipeline_start", run_id=run_id)
    config = {"configurable": {"thread_id": run_id}}

    try:
        graph = get_graph()
        final_state = await graph.ainvoke(
            initial_state(run_id, started_at.isoformat()), config=config
        )

        # ainvoke returns at the await_approval interrupt as well as at END —
        # a non-empty snapshot.next means the run is paused for human review.
        snapshot = await graph.aget_state(config)
        paused = bool(snapshot.next)

        stats = dict(final_state.get("daily_stats") or {})
        if paused:
            stats.setdefault("pending_approvals",
                             len(final_state.get("pending_approvals", [])))
            stats["paused_for_approval"] = True
        errors = final_state.get("errors", [])
        result = {
            "run_id": run_id,
            "status": "completed",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "errors": errors,
        }
        logger.info("morning_pipeline_complete", run_id=run_id, paused=paused, **stats)
    except Exception as exc:
        logger.error("morning_pipeline_failed", run_id=run_id, error=str(exc))
        result = {
            "run_id": run_id,
            "status": "failed",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "stats": {},
            "errors": [str(exc)],
        }

    if owns_row:
        try:
            sb.table("pipeline_runs").update({
                "status": result["status"],
                "completed_at": result["completed_at"],
                "stats": result["stats"],
                "errors": result["errors"],
            }).eq("id", run_id).execute()
        except Exception as exc:
            logger.error("morning_pipeline.run_row_update_failed", error=str(exc))

    return result
