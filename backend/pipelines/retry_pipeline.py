from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
import structlog
from agents.resume import agent as resume_agent
from browser.form_filler import fill_application

logger = structlog.get_logger()


async def run(failed_applications: list[dict] | None = None) -> dict:
    """
    Retry failed job applications.
    In production this would pull failed apps from Supabase;
    for now operates on the list passed in or does a no-op.
    """
    run_id = str(uuid4())
    started_at = datetime.now(timezone.utc)
    logger.info("retry_pipeline_start", run_id=run_id)

    apps_to_retry = failed_applications or []
    retried = 0
    newly_failed = 0

    for app in apps_to_retry:
        job = app.get("job", {})
        job_url = job.get("url", "")
        resume_data = app.get("resume", {})
        tailored_text = resume_data.get("tailored_text", "")

        if not job_url:
            logger.warning("retry_skip_no_url", job=job.get("title"))
            continue

        try:
            result = await fill_application(
                job_url=job_url,
                resume_path="./resume.pdf",
                cover_letter=tailored_text[:2000] if tailored_text else None,
            )
            if result["success"]:
                retried += 1
                logger.info("retry_success", url=job_url)
            else:
                newly_failed += 1
                logger.warning("retry_failed_again", url=job_url, error=result.get("error"))
        except Exception as exc:
            newly_failed += 1
            logger.error("retry_exception", url=job_url, error=str(exc))

    stats = {
        "applications_retried": len(apps_to_retry),
        "retry_success": retried,
        "retry_failed": newly_failed,
    }
    logger.info("retry_pipeline_complete", run_id=run_id, **stats)
    return {
        "run_id": run_id,
        "status": "completed",
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "errors": [],
    }
