from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query
from core.supabase_client import get_supabase_client
import structlog

router = APIRouter(prefix="/inbox", tags=["inbox"])
logger = structlog.get_logger()


# ── 1. List emails (paginated, filterable) ────────────────────────────────────

@router.get("")
async def list_inbox(
    classification: str | None = Query(None),
    pipeline_stage: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    days: int | None = Query(None),
):
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")

        query = sb.table("inbox_emails").select("*")
        if classification:
            query = query.eq("classification", classification)
        if pipeline_stage:
            query = query.eq("pipeline_stage", pipeline_stage)
        if days:
            since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte("received_at", since)

        result = query.order("received_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error("inbox.get.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── 2. List threads — MUST come before /{email_id} ───────────────────────────

@router.get("/threads")
async def list_email_threads(
    stage: str | None = Query(None),
    days: int = Query(30),
):
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")

        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        query = sb.table("email_threads").select("*").gte("last_email_at", since)
        if stage:
            query = query.eq("pipeline_stage", stage)

        result = query.order("last_email_at", desc=True).execute()
        return result.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error("inbox.threads.get.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── 3. Update thread pipeline stage ──────────────────────────────────────────

@router.patch("/threads/{thread_id}/stage")
async def update_thread_stage(thread_id: str, body: dict):
    stage = body.get("stage")
    if not stage:
        raise HTTPException(status_code=422, detail="stage is required")
    valid = {"classified", "screening", "interview", "offer", "rejected"}
    if stage not in valid:
        raise HTTPException(status_code=422, detail=f"stage must be one of {valid}")
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")

        sb.table("email_threads").update({"pipeline_stage": stage}).eq("thread_id", thread_id).execute()
        sb.table("inbox_emails").update({"pipeline_stage": stage}).eq("thread_id", thread_id).execute()
        logger.info("inbox.thread.stage_updated", thread_id=thread_id, stage=stage)
        return {"thread_id": thread_id, "stage": stage}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("inbox.thread.stage_update.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── 4. Send reply for an email ────────────────────────────────────────────────

@router.post("/{email_id}/send-reply")
async def send_reply(email_id: str, body: dict):
    reply_text = body.get("reply")
    if not reply_text:
        raise HTTPException(status_code=422, detail="reply is required")
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")

        now = datetime.now(timezone.utc).isoformat()
        sb.table("inbox_emails").update({
            "reply_sent": True,
            "reply_sent_at": now,
        }).eq("id", email_id).execute()
        logger.info("inbox.reply_sent", email_id=email_id)
        return {"email_id": email_id, "sent_at": now}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("inbox.send_reply.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── 5. Get single email — catch-all LAST ─────────────────────────────────────

@router.get("/{email_id}")
async def get_email(email_id: str):
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")

        result = sb.table("inbox_emails").select("*").eq("id", email_id).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Email not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("inbox.get_email.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
