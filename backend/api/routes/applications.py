from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from models.schemas import Application, ApplicationStatus
from core.supabase_client import get_supabase_client
import structlog

router = APIRouter(prefix="/applications", tags=["applications"])
logger = structlog.get_logger()

_JOIN = "*, jobs(*), resumes(*)"

# Allowed status transitions: pending → approved | rejected, approved → applied.
# Retry pipeline separately re-queues failed → pending.
_TRANSITIONS: dict[str, set[str]] = {
    "approved": {"pending"},
    "rejected": {"pending"},
    "applied": {"approved"},
}


def _remap(row: dict) -> dict:
    """Rename Supabase FK join keys to match Application model fields."""
    row["job"] = row.pop("jobs", None)
    row["resume"] = row.pop("resumes", None)
    return row


def _notify_graph(application_id: UUID, decision: str, app: dict) -> None:
    """Feed the human decision into the paused LangGraph run (fire-and-forget).

    Supabase is already updated by the time this runs; a graph failure must
    never fail the API response. Imported lazily so the routes module doesn't
    drag in langgraph/agents at startup."""
    try:
        from orchestrator.approvals import schedule_decision
        schedule_decision(str(application_id), decision, app)
    except Exception as e:
        logger.error("graph_resume_schedule_failed",
                     application_id=str(application_id), decision=decision, error=str(e))


def _get_app_or_404(sb, application_id: UUID) -> dict:
    result = sb.table("applications").select("*, jobs(*)").eq("id", str(application_id)).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Application not found")
    return result.data[0]


def _guard_transition(app: dict, new_status: str) -> None:
    current = app.get("status")
    if current not in _TRANSITIONS[new_status]:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot mark application '{new_status}' from status '{current}'",
        )


def _transition(sb, application_id: UUID, app: dict, new_status: str, extra: dict | None = None) -> str:
    """Apply a guarded status transition. Returns the update timestamp.

    The update is filtered on the current status so a concurrent click that
    already moved the row can't be double-applied.
    """
    _guard_transition(app, new_status)
    now = datetime.now(timezone.utc).isoformat()
    payload = {"status": new_status, "updated_at": now, **(extra or {})}
    result = (
        sb.table("applications")
        .update(payload)
        .eq("id", str(application_id))
        .eq("status", app["status"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=409, detail="Application status changed concurrently — refresh and retry")
    return now


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
        raise HTTPException(status_code=500, detail="Internal server error")


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
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{application_id}/approve")
async def approve_application(application_id: UUID):
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")

        app = _get_app_or_404(sb, application_id)
        _transition(sb, application_id, app, "approved",
                    extra={"approved_at": datetime.now(timezone.utc).isoformat()})

        sb.table("jobs").update({"status": "approved"}).eq("id", app["job_id"]).execute()
        _notify_graph(application_id, "approved", app)

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
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{application_id}/reject")
async def reject_application(application_id: UUID):
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")

        app = _get_app_or_404(sb, application_id)
        _transition(sb, application_id, app, "rejected")
        sb.table("jobs").update({"status": "rejected"}).eq("id", app["job_id"]).execute()
        _notify_graph(application_id, "rejected", app)

        logger.info("application_rejected", application_id=str(application_id))
        return {"message": "Application rejected", "id": str(application_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("reject_application_error", application_id=str(application_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{application_id}/mark-applied")
async def mark_applied(application_id: UUID):
    """User has manually submitted the application — record the timestamp."""
    sb = get_supabase_client()
    if sb is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    try:
        app = _get_app_or_404(sb, application_id)
        now = datetime.now(timezone.utc).isoformat()
        _transition(sb, application_id, app, "applied", extra={"submitted_at": now})

        sb.table("jobs").update({"status": "applied"}).eq("id", app["job_id"]).execute()

        today = datetime.now(timezone.utc).date().isoformat()
        existing = sb.table("analytics").select("id, applications_submitted").eq("date", today).execute()
        if existing.data:
            current = existing.data[0].get("applications_submitted") or 0
            sb.table("analytics").update({
                "applications_submitted": current + 1
            }).eq("date", today).execute()
        else:
            sb.table("analytics").insert({
                "date": today,
                "applications_submitted": 1,
            }).execute()

        # Resume the paused graph run (or seed a follow-on) so recruiter
        # outreach kicks off for this now-applied job.
        _notify_graph(application_id, "applied", app)

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
        raise HTTPException(status_code=500, detail="Internal server error")
