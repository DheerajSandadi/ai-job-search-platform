from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from models.schemas import Application, ApplicationStatus
from core.supabase_client import get_supabase_client
import structlog

router = APIRouter(prefix="/applications", tags=["applications"])
logger = structlog.get_logger()

_JOIN = "*, jobs(*), resumes(*)"


def _remap(row: dict) -> dict:
    """Rename Supabase FK join keys to match Application model fields."""
    row["job"] = row.pop("jobs", None)
    row["resume"] = row.pop("resumes", None)
    return row


async def _fetch_application(sb, application_id: str) -> dict:
    result = sb.table("applications").select(_JOIN).eq("id", application_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Application not found")
    return _remap(result.data[0])


@router.get("", response_model=list[Application])
async def list_applications(
    status: ApplicationStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[Application]:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        query = sb.table("applications").select(_JOIN)
        if status:
            query = query.eq("status", status.value)
        query = query.order("created_at", desc=True)
        query = query.range((page - 1) * page_size, page * page_size - 1)
        result = query.execute()
        return [_remap(row) for row in result.data]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_applications_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending", response_model=list[Application])
async def list_pending_applications() -> list[Application]:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        result = (
            sb.table("applications")
            .select(_JOIN)
            .eq("status", ApplicationStatus.PENDING.value)
            .order("created_at", desc=True)
            .execute()
        )
        return [_remap(row) for row in result.data]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_pending_applications_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{application_id}/approve")
async def approve_application(application_id: UUID):
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")

        result = sb.table("applications").select("*, jobs(*)").eq("id", str(application_id)).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Application not found")
        app = result.data[0]

        now = datetime.now(timezone.utc).isoformat()
        sb.table("applications").update({
            "status": "approved",
            "approved_at": now,
            "updated_at": now,
        }).eq("id", str(application_id)).execute()

        sb.table("jobs").update({"status": "approved"}).eq("id", app["job_id"]).execute()

        job = app.get("jobs") or {}
        logger.info("application_approved", application_id=str(application_id), job=job.get("title"))

        return {
            "message": "Application approved",
            "id": str(application_id),
            "job_url": job.get("url"),
            "job_title": job.get("title"),
            "company": job.get("company"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("approve_application_error", application_id=str(application_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{application_id}/reject")
async def reject_application(application_id: UUID):
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")

        result = sb.table("applications").select("*, jobs(*)").eq("id", str(application_id)).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Application not found")
        app = result.data[0]

        now = datetime.now(timezone.utc).isoformat()
        sb.table("applications").update({"status": "rejected", "updated_at": now}).eq("id", str(application_id)).execute()
        sb.table("jobs").update({"status": "rejected"}).eq("id", app["job_id"]).execute()

        logger.info("application_rejected", application_id=str(application_id))
        return {"message": "Application rejected", "id": str(application_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("reject_application_error", application_id=str(application_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{application_id}/mark-applied")
async def mark_applied(application_id: UUID):
    """User has manually submitted the application — record the timestamp."""
    sb = get_supabase_client()
    if sb is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    try:
        result = sb.table("applications").select("*, jobs(*)").eq("id", str(application_id)).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Application not found")
        app = result.data[0]

        now = datetime.now(timezone.utc).isoformat()

        sb.table("applications").update({
            "status": "applied",
            "submitted_at": now,
            "updated_at": now,
        }).eq("id", str(application_id)).execute()

        sb.table("jobs").update({"status": "applied"}).eq("id", app["job_id"]).execute()

        today = datetime.now(timezone.utc).date().isoformat()
        existing = sb.table("analytics").select("id, applications_submitted").eq("date", today).execute()
        if existing.data:
            current = existing.data[0].get("applications_submitted", 0)
            sb.table("analytics").update({
                "applications_submitted": current + 1
            }).eq("date", today).execute()

        job = app.get("jobs") or {}
        logger.info("applications.mark_applied", application_id=str(application_id), job=job.get("title"))

        return {
            "message": "Marked as applied",
            "id": str(application_id),
            "applied_at": now,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("applications.mark_applied.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
