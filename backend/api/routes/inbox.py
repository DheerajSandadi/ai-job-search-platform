import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from fastapi import APIRouter, HTTPException, Query
from core.supabase_client import get_supabase_client
from core.gmail_client import get_gmail_service
import structlog

router = APIRouter()
logger = structlog.get_logger()

_VALID_STAGES = {"classified", "screening", "interview", "offer", "rejected"}


@router.get("/inbox")
async def get_inbox(
    classification: str | None = Query(None),
    pipeline_stage: str | None = Query(None),
    days: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    try:
        sb = get_supabase_client()
        query = sb.table("inbox_emails").select("*")

        if classification:
            query = query.eq("classification", classification)
        if pipeline_stage:
            query = query.eq("pipeline_stage", pipeline_stage)
        if days:
            since = (datetime.utcnow() - timedelta(days=days)).isoformat()
            query = query.gte("received_at", since)

        result = query.order("received_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []

    except Exception as e:
        logger.error("inbox.get.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inbox/threads")
async def get_email_threads(
    stage: str | None = Query(None),
    days: int = Query(30),
):
    try:
        sb = get_supabase_client()
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        query = sb.table("email_threads").select("*").gte("last_email_at", since)
        if stage:
            query = query.eq("pipeline_stage", stage)
        result = query.order("last_email_at", desc=True).execute()
        return result.data or []

    except Exception as e:
        logger.error("inbox.threads.get.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/inbox/threads/{thread_id}/stage")
async def update_thread_stage(thread_id: str, body: dict):
    stage = body.get("stage")
    if stage not in _VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    try:
        sb = get_supabase_client()
        sb.table("email_threads").update({
            "pipeline_stage": stage,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("thread_id", thread_id).execute()
        sb.table("inbox_emails").update({
            "pipeline_stage": stage,
        }).eq("thread_id", thread_id).execute()

        logger.info("inbox.thread.stage_updated", thread_id=thread_id, stage=stage)
        return {"message": "Stage updated", "thread_id": thread_id, "stage": stage}

    except Exception as e:
        logger.error("inbox.thread.stage_update.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inbox/{email_id}/send-reply")
async def send_reply(email_id: str):
    try:
        sb = get_supabase_client()
        result = sb.table("inbox_emails").select("*").eq("id", email_id).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Email not found")

        email = result.data[0]
        draft = email.get("draft_reply")
        if not draft:
            raise HTTPException(status_code=400, detail="No draft reply found")

        settings_row = sb.table("settings").select(
            "gmail_access_token, gmail_refresh_token"
        ).limit(1).execute()
        if not settings_row.data:
            raise HTTPException(status_code=500, detail="Gmail not connected")

        row = settings_row.data[0]
        service = get_gmail_service(
            access_token=row.get("gmail_access_token"),
            refresh_token=row.get("gmail_refresh_token"),
        )
        if not service:
            raise HTTPException(status_code=500, detail="Gmail service unavailable")

        msg = MIMEText(draft)
        msg["To"] = email.get("sender_email", "")
        msg["Subject"] = f"Re: {email.get('subject', '')}"
        msg["In-Reply-To"] = email.get("gmail_message_id", "")
        msg["References"] = email.get("gmail_message_id", "")

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": email.get("thread_id")},
        ).execute()

        now = datetime.utcnow().isoformat()
        sb.table("inbox_emails").update({
            "reply_sent": True,
            "reply_sent_at": now,
        }).eq("id", email_id).execute()

        logger.info("inbox.reply_sent", email_id=email_id)
        return {"message": "Reply sent", "email_id": email_id, "sent_at": now}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("inbox.send_reply.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inbox/{email_id}")
async def get_inbox_email(email_id: str):
    try:
        sb = get_supabase_client()
        result = sb.table("inbox_emails").select("*").eq("id", email_id).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Email not found")
        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("inbox.get_email.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
