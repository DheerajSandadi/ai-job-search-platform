from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
import structlog
from agents.inbox import agent as inbox_agent

logger = structlog.get_logger()


async def run() -> dict:
    """Process new Gmail inbox messages: classify and draft replies."""
    run_id = str(uuid4())
    started_at = datetime.now(timezone.utc)
    logger.info("inbox_pipeline_start", run_id=run_id)

    try:
        emails = inbox_agent.run(mark_as_read=True)
        actionable = [e for e in emails if e.get("classification") not in ("unrelated", None)]
        stats = {
            "emails_processed": len(emails),
            "actionable": len(actionable),
            "replies_drafted": sum(1 for e in emails if e.get("draft_reply")),
        }
        logger.info("inbox_pipeline_complete", run_id=run_id, **stats)
        return {
            "run_id": run_id,
            "status": "completed",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "errors": [],
        }
    except Exception as exc:
        logger.error("inbox_pipeline_failed", run_id=run_id, error=str(exc))
        return {
            "run_id": run_id,
            "status": "failed",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "stats": {},
            "errors": [str(exc)],
        }
