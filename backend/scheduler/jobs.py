from __future__ import annotations

import asyncio
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.config import settings

logger = structlog.get_logger()

_scheduler: AsyncIOScheduler | None = None


async def _run_morning() -> None:
    from pipelines.morning_pipeline import run
    logger.info("scheduler_trigger", pipeline="morning")
    await run()


async def _run_inbox() -> None:
    from pipelines.inbox_pipeline import run
    logger.info("scheduler_trigger", pipeline="inbox")
    await run()


async def _run_retry() -> None:
    from pipelines.retry_pipeline import run
    logger.info("scheduler_trigger", pipeline="retry")
    await run()


def _parse_cron(expr: str) -> dict:
    parts = expr.strip().split()
    if len(parts) != 5:
        return {"minute": "0", "hour": "6"}
    minute, hour, day, month, day_of_week = parts
    return {
        "minute": minute,
        "hour": hour,
        "day": day,
        "month": month,
        "day_of_week": day_of_week,
    }


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="America/Los_Angeles")

    morning_cron = _parse_cron(settings.MORNING_PIPELINE_CRON)
    retry_cron = _parse_cron(settings.RETRY_PIPELINE_CRON)

    _scheduler.add_job(
        _run_morning,
        trigger=CronTrigger(**morning_cron),
        id="morning_pipeline",
        replace_existing=True,
    )
    _scheduler.add_job(
        _run_inbox,
        trigger=CronTrigger(minute="*/15"),  # every 15 min
        id="inbox_pipeline",
        replace_existing=True,
    )
    _scheduler.add_job(
        _run_retry,
        trigger=CronTrigger(**retry_cron),
        id="retry_pipeline",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "scheduler_started",
        morning=settings.MORNING_PIPELINE_CRON,
        retry=settings.RETRY_PIPELINE_CRON,
        inbox="every 15 min",
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
