from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.schemas import PipelineRun, PipelineRunStatus, PipelineStatusResponse, PipelineType
from core.supabase_client import get_supabase_client
import structlog

router = APIRouter(prefix="/pipelines", tags=["pipelines"])
logger = structlog.get_logger()


async def _execute_pipeline(key: str, run_id: str) -> None:
    sb = get_supabase_client()
    try:
        if key == "morning":
            from pipelines.morning_pipeline import run
        elif key == "inbox":
            from pipelines.inbox_pipeline import run
        else:
            from pipelines.retry_pipeline import run

        result = await run()
        if sb:
            sb.table("pipeline_runs").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "stats": result.get("stats", {}),
                "errors": result.get("errors", []),
            }).eq("id", run_id).execute()
    except Exception as exc:
        logger.error("pipeline_execution_error", pipeline=key, run_id=run_id, error=str(exc))
        if sb:
            sb.table("pipeline_runs").update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "errors": [str(exc)],
            }).eq("id", run_id).execute()

    logger.info("pipeline_finished", pipeline=key, run_id=run_id)


def _latest_run(sb, pipeline_type: str, enum_val: PipelineType) -> PipelineRun:
    result = (
        sb.table("pipeline_runs")
        .select("*")
        .eq("pipeline_type", pipeline_type)
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return PipelineRun(pipeline_type=enum_val, status=PipelineRunStatus.IDLE)
    return PipelineRun(**result.data[0])


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status() -> PipelineStatusResponse:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        return PipelineStatusResponse(
            morning=_latest_run(sb, "morning", PipelineType.MORNING),
            retry=_latest_run(sb, "retry", PipelineType.RETRY),
            inbox=_latest_run(sb, "inbox", PipelineType.INBOX),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_pipeline_status_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/morning/trigger", response_model=PipelineRun)
async def trigger_morning_pipeline(background_tasks: BackgroundTasks) -> PipelineRun:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        running = (
            sb.table("pipeline_runs")
            .select("id")
            .eq("pipeline_type", "morning")
            .eq("status", "running")
            .limit(1)
            .execute()
        )
        if running.data:
            raise HTTPException(status_code=409, detail="Morning pipeline already running")
        inserted = sb.table("pipeline_runs").insert({
            "pipeline_type": "morning",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        run_id = inserted.data[0]["id"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("trigger_morning_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    background_tasks.add_task(_execute_pipeline, "morning", run_id)
    logger.info("morning_pipeline_triggered", run_id=run_id)
    return PipelineRun(**inserted.data[0])


@router.post("/retry/trigger", response_model=PipelineRun)
async def trigger_retry_pipeline(background_tasks: BackgroundTasks) -> PipelineRun:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        running = (
            sb.table("pipeline_runs")
            .select("id")
            .eq("pipeline_type", "retry")
            .eq("status", "running")
            .limit(1)
            .execute()
        )
        if running.data:
            raise HTTPException(status_code=409, detail="Retry pipeline already running")
        inserted = sb.table("pipeline_runs").insert({
            "pipeline_type": "retry",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        run_id = inserted.data[0]["id"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("trigger_retry_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    background_tasks.add_task(_execute_pipeline, "retry", run_id)
    logger.info("retry_pipeline_triggered", run_id=run_id)
    return PipelineRun(**inserted.data[0])


@router.post("/inbox/trigger", response_model=PipelineRun)
async def trigger_inbox_pipeline(background_tasks: BackgroundTasks) -> PipelineRun:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        running = (
            sb.table("pipeline_runs")
            .select("id")
            .eq("pipeline_type", "inbox")
            .eq("status", "running")
            .limit(1)
            .execute()
        )
        if running.data:
            raise HTTPException(status_code=409, detail="Inbox pipeline already running")
        inserted = sb.table("pipeline_runs").insert({
            "pipeline_type": "inbox",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        run_id = inserted.data[0]["id"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("trigger_inbox_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    background_tasks.add_task(_execute_pipeline, "inbox", run_id)
    logger.info("inbox_pipeline_triggered", run_id=run_id)
    return PipelineRun(**inserted.data[0])
