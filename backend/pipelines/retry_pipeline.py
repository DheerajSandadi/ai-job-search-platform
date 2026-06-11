import asyncio
import structlog
from concurrent.futures import ThreadPoolExecutor

from core.supabase_client import get_supabase_client

logger = structlog.get_logger()
_executor = ThreadPoolExecutor(max_workers=2)


async def run() -> dict:
    """
    Retry pipeline — runs at 9AM daily.
    Queries Supabase for failed applications with retry_count < 3.
    Re-queues them as pending for manual re-apply, increments retry_count.
    """
    logger.info("retry_pipeline.start")
    sb = get_supabase_client()

    stats = {
        "found": 0,
        "retried": 0,
        "max_retries_reached": 0,
        "errors": 0,
    }

    try:
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
            return stats

        logger.info("retry_pipeline.found", count=len(failed_apps))

        for app in failed_apps:
            app_id = app["id"]
            job = app.get("jobs") or {}
            retry_count = app.get("retry_count", 0)

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

        logger.info("retry_pipeline.complete", **stats)
        return stats

    except Exception as e:
        logger.error("retry_pipeline.error", error=str(e))
        stats["errors"] += 1
        return stats
