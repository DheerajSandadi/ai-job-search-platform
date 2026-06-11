from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
import structlog
from orchestrator.graph import morning_graph
from orchestrator.state import PipelineState

logger = structlog.get_logger()


async def run() -> dict:
    """Execute the full morning pipeline via LangGraph."""
    run_id = str(uuid4())
    started_at = datetime.now(timezone.utc)
    logger.info("morning_pipeline_start", run_id=run_id)

    initial_state: PipelineState = {
        "run_id": run_id,
        "started_at": started_at,
        "current_step": "start",
        "errors": [],
        "raw_jobs": [],
        "scored_jobs": [],
        "approved_jobs": [],
        "pending_approvals": [],
        "tailored_resumes": [],
        "submitted_applications": [],
        "failed_applications": [],
        "recruiters": [],
        "outreach_queue": [],
        "outreach_sent": [],
        "daily_stats": {},
    }

    try:
        final_state = await morning_graph.invoke(initial_state)
        stats = final_state.get("daily_stats", {})
        logger.info("morning_pipeline_complete", run_id=run_id, **stats)
        return {
            "run_id": run_id,
            "status": "completed",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "errors": final_state.get("errors", []),
        }
    except Exception as exc:
        logger.error("morning_pipeline_failed", run_id=run_id, error=str(exc))
        return {
            "run_id": run_id,
            "status": "failed",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "stats": {},
            "errors": [str(exc)],
        }
