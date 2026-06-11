from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from models.schemas import Job, JobStatus
from core.supabase_client import get_supabase_client
import structlog

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = structlog.get_logger()


@router.get("", response_model=list[Job])
async def list_jobs(
    source: str | None = Query(None),
    status: JobStatus | None = Query(None),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[Job]:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        query = sb.table("jobs").select("*")
        if source:
            query = query.eq("source", source)
        if status:
            query = query.eq("status", status.value)
        if min_score > 0.0:
            query = query.gte("relevance_score", min_score)
        query = query.order("created_at", desc=True)
        query = query.range((page - 1) * page_size, page * page_size - 1)
        result = query.execute()
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_jobs_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: UUID) -> Job:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        result = sb.table("jobs").select("*").eq("id", str(job_id)).limit(1).execute()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_job_error", job_id=str(job_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return result.data[0]
