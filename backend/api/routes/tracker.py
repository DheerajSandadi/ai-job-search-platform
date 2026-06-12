"""
Gmail tracker routes — applications pipeline, dashboard stats, AI follow-ups.
Data stored in Supabase tracker_applications + inbox_emails tables.
"""
from __future__ import annotations

import asyncio
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from core.anthropic_client import get_anthropic_client, HAIKU, SONNET
from core.supabase_client import get_supabase_client

router = APIRouter()
logger = structlog.get_logger()

_executor = ThreadPoolExecutor(max_workers=2)
_classify_state: dict = {"running": False, "processed": 0, "total": 0}

STAGE_PRIORITY = {"applied": 1, "screen": 2, "interview": 3, "offer": 4, "rejected": 5}

CLASSIFY_PROMPT = """You are an AI assistant helping a job seeker track their job applications via email.

Analyze the following email and extract structured information.

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "classification": "one of: application_confirmation | recruiter_reply | interview_request | offer | rejection | followup_needed | irrelevant",
  "company_name": "string or null",
  "role_title": "string or null",
  "recruiter_name": "string or null",
  "status": "one of: applied | screen | interview | offer | rejected | unknown",
  "requires_followup": true or false,
  "followup_due_days": integer or null,
  "confidence": 0.0 to 1.0
}}

Email:
Subject: {subject}
From: {sender}
Body: {body}"""


# ─── INTERNAL HELPERS ────────────────────────────────────────────────────────

def _classify_single(email: dict) -> dict:
    client = get_anthropic_client()
    prompt = CLASSIFY_PROMPT.format(
        subject=email.get("subject", ""),
        sender=email.get("sender_email", ""),
        body=(email.get("full_body") or email.get("body_preview") or "")[:3000],
    )
    try:
        response = client.call_claude(
            model=HAIKU,
            system="Return only valid JSON. No markdown.",
            user=prompt,
            max_tokens=400,
        )
        response = response.strip()
        if response.startswith("```"):
            response = re.sub(r"```json?\n?", "", response).rstrip("`").strip()
        return json.loads(response)
    except Exception as e:
        logger.error("tracker.classify.single.error", error=str(e))
        return {"classification": "irrelevant", "confidence": 0.0}


def _upsert_application(email: dict, result: dict, sb) -> Optional[str]:
    company = result.get("company_name")
    status = result.get("status", "applied")
    classification = result.get("classification", "irrelevant")

    if not company or classification == "irrelevant":
        return None
    if status not in STAGE_PRIORITY:
        status = "applied"

    app = None
    thread_id = email.get("thread_id")
    if thread_id:
        sibling = sb.table("inbox_emails").select("application_id").eq(
            "thread_id", thread_id
        ).not_.is_("application_id", "null").limit(1).execute()
        if sibling.data:
            app_id = sibling.data[0]["application_id"]
            app_result = sb.table("tracker_applications").select("*").eq("id", app_id).execute()
            if app_result.data:
                app = app_result.data[0]

    role = result.get("role_title")
    if not app and company and role:
        existing = sb.table("tracker_applications").select("*").eq(
            "company_name", company
        ).eq("role_title", role).execute()
        if existing.data:
            app = existing.data[0]

    if app:
        current_priority = STAGE_PRIORITY.get(app.get("status", ""), 0)
        new_priority = STAGE_PRIORITY.get(status, 0)
        updates: dict = {"updated_at": datetime.utcnow().isoformat()}
        if new_priority > current_priority:
            updates["status"] = status
        updates["latest_email_at"] = email.get("received_at") or datetime.utcnow().isoformat()
        updates["email_count"] = (app.get("email_count") or 0) + 1
        sb.table("tracker_applications").update(updates).eq("id", app["id"]).execute()
        return str(app["id"])
    else:
        new_app = sb.table("tracker_applications").insert({
            "company_name": company,
            "role_title": role,
            "status": status,
            "applied_date": email.get("received_at"),
            "source": "gmail_auto",
            "email_count": 1,
            "latest_email_at": email.get("received_at"),
        }).execute()
        if new_app.data:
            return str(new_app.data[0]["id"])
    return None


def _run_classify_batch():
    _classify_state["running"] = True
    try:
        sb = get_supabase_client()
        while True:
            batch = sb.table("inbox_emails").select("*").is_(
                "classification", "null"
            ).limit(50).execute()
            if not batch.data:
                break
            for email in batch.data:
                try:
                    result = _classify_single(email)
                    followup_due = None
                    days = result.get("followup_due_days")
                    if result.get("requires_followup") and days:
                        followup_due = (datetime.utcnow() + timedelta(days=int(days))).isoformat()

                    app_id = _upsert_application(email, result, sb)

                    updates: dict = {
                        "classification": result.get("classification", "irrelevant"),
                        "company_name": result.get("company_name"),
                        "role_title": result.get("role_title"),
                        "recruiter_name": result.get("recruiter_name"),
                        "pipeline_stage": result.get("status", "classified"),
                        "requires_followup": result.get("requires_followup", False),
                        "ai_confidence": result.get("confidence"),
                    }
                    if followup_due:
                        updates["followup_due_date"] = followup_due
                    if app_id:
                        updates["application_id"] = app_id

                    sb.table("inbox_emails").update(updates).eq("id", email["id"]).execute()
                    _classify_state["processed"] += 1
                except Exception as e:
                    logger.error("tracker.classify.email_error", id=email.get("id"), error=str(e))
                    continue
    except Exception as e:
        logger.error("tracker.classify.run_error", error=str(e))
    finally:
        _classify_state["running"] = False


# ─── CLASSIFY ENDPOINTS ───────────────────────────────────────────────────────

@router.get("/tracker/classify/status")
async def get_classify_status():
    sb = get_supabase_client()
    try:
        total_res = sb.table("inbox_emails").select("id", count="exact").execute()
        classified_res = sb.table("inbox_emails").select("id", count="exact").not_.is_(
            "classification", "null"
        ).execute()
        total_count = total_res.count or len(total_res.data)
        classified_count = classified_res.count or len(classified_res.data)
        return {
            **_classify_state,
            "total_emails": total_count,
            "classified": classified_count,
            "unclassified": total_count - classified_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tracker/classify")
async def start_classify(background_tasks: BackgroundTasks):
    if _classify_state["running"]:
        return {"status": "already_running", **_classify_state}

    sb = get_supabase_client()
    unclassified = sb.table("inbox_emails").select("id", count="exact").is_(
        "classification", "null"
    ).execute()
    total = unclassified.count or len(unclassified.data)
    _classify_state["total"] = total
    _classify_state["processed"] = 0

    background_tasks.add_task(_run_classify_batch)
    return {"status": "started", "unclassified": total}


# ─── TRACKER APPLICATIONS ─────────────────────────────────────────────────────

class CreateAppRequest(BaseModel):
    company_name: str
    role_title: str
    status: str = "applied"
    applied_date: Optional[str] = None
    job_url: Optional[str] = None
    notes: Optional[str] = None


class UpdateAppRequest(BaseModel):
    company_name: Optional[str] = None
    role_title: Optional[str] = None
    status: Optional[str] = None
    applied_date: Optional[str] = None
    job_url: Optional[str] = None
    notes: Optional[str] = None


@router.get("/tracker/applications")
async def get_tracker_applications(
    status: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(200, ge=1, le=500),
):
    sb = get_supabase_client()
    try:
        query = sb.table("tracker_applications").select("*")
        if status:
            query = query.eq("status", status)
        if company:
            query = query.ilike("company_name", f"%{company}%")
        if date_from:
            query = query.gte("created_at", date_from)
        result = query.order("created_at", desc=True).range(
            (page - 1) * per_page, page * per_page - 1
        ).execute()

        count_query = sb.table("tracker_applications").select("id", count="exact")
        if status:
            count_query = count_query.eq("status", status)
        total_result = count_query.execute()

        return {
            "total": total_result.count or len(total_result.data),
            "applications": result.data or [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tracker/applications")
async def create_tracker_application(req: CreateAppRequest):
    sb = get_supabase_client()
    try:
        result = sb.table("tracker_applications").insert({
            "company_name": req.company_name,
            "role_title": req.role_title,
            "status": req.status,
            "applied_date": req.applied_date,
            "source": "manual",
            "job_url": req.job_url,
            "notes": req.notes,
            "email_count": 0,
        }).execute()
        return {"id": result.data[0]["id"], "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tracker/applications/{app_id}/status")
async def update_tracker_status(app_id: str, status: str = Query(...)):
    sb = get_supabase_client()
    try:
        sb.table("tracker_applications").update({
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", app_id).execute()
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tracker/applications/{app_id}")
async def update_tracker_application(app_id: str, req: UpdateAppRequest):
    sb = get_supabase_client()
    try:
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        updates["updated_at"] = datetime.utcnow().isoformat()
        sb.table("tracker_applications").update(updates).eq("id", app_id).execute()
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tracker/applications/{app_id}")
async def delete_tracker_application(app_id: str):
    sb = get_supabase_client()
    try:
        sb.table("tracker_applications").delete().eq("id", app_id).execute()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tracker/applications/{app_id}/emails")
async def get_application_emails(app_id: str):
    sb = get_supabase_client()
    try:
        result = sb.table("inbox_emails").select("*").eq(
            "application_id", app_id
        ).order("received_at", desc=True).execute()
        return {"emails": result.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@router.get("/tracker/dashboard/overview")
async def get_dashboard_overview():
    sb = get_supabase_client()
    try:
        confirmations = sb.table("inbox_emails").select("id", count="exact").eq(
            "classification", "application_confirmation"
        ).execute()
        interviews = sb.table("inbox_emails").select("id", count="exact").in_(
            "classification", ["interview_request", "interview_invite"]
        ).execute()
        offers = sb.table("inbox_emails").select("id", count="exact").eq(
            "classification", "offer"
        ).execute()
        rejections = sb.table("inbox_emails").select("id", count="exact").in_(
            "classification", ["rejection", "rejected"]
        ).execute()
        try:
            followups = sb.table("inbox_emails").select("id", count="exact").eq(
                "requires_followup", True
            ).execute()
        except Exception:
            followups = type("R", (), {"count": 0})()
        try:
            total_apps = sb.table("tracker_applications").select("id", count="exact").execute()
        except Exception:
            total_apps = type("R", (), {"count": 0})()
        total_emails = sb.table("inbox_emails").select("id", count="exact").execute()

        c = confirmations.count or 0
        i = interviews.count or 0
        o = offers.count or 0
        r = rejections.count or 0
        response_rate = round((i + r + o) / max(c, 1) * 100, 1)

        return {
            "total_applications": total_apps.count or 0,
            "total_emails": total_emails.count or 0,
            "interviews": i,
            "offers": o,
            "rejections": r,
            "response_rate": response_rate,
            "followups_due": followups.count or 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tracker/dashboard/activity")
async def get_activity(days: int = Query(30)):
    sb = get_supabase_client()
    try:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        result = sb.table("inbox_emails").select(
            "received_at, direction"
        ).gte("received_at", since).execute()

        by_date: dict = {}
        for e in result.data or []:
            if e.get("received_at"):
                date_key = e["received_at"][:10]
                if date_key not in by_date:
                    by_date[date_key] = {"date": date_key, "sent": 0, "received": 0, "total": 0}
                by_date[date_key]["total"] += 1
                if e.get("direction") == "sent":
                    by_date[date_key]["sent"] += 1
                else:
                    by_date[date_key]["received"] += 1

        return {"activity": sorted(by_date.values(), key=lambda x: x["date"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tracker/dashboard/top-companies")
async def get_top_companies():
    sb = get_supabase_client()
    try:
        result = sb.table("inbox_emails").select(
            "company_name"
        ).not_.is_("company_name", "null").execute()

        counts: dict = {}
        for e in result.data or []:
            c = e.get("company_name", "")
            if c:
                counts[c] = counts.get(c, 0) + 1

        sorted_companies = sorted(counts.items(), key=lambda x: -x[1])[:10]
        return [{"company": k, "count": v} for k, v in sorted_companies]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tracker/dashboard/email-stats")
async def get_email_stats():
    sb = get_supabase_client()
    try:
        result = sb.table("inbox_emails").select("classification").execute()
        counts: dict = {}
        for e in result.data or []:
            c = e.get("classification")
            if c:
                counts[c] = counts.get(c, 0) + 1
        return {"by_classification": counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── AI FOLLOW-UP ─────────────────────────────────────────────────────────────

@router.get("/tracker/emails/{email_id}/followup-draft")
async def get_followup_draft(email_id: str):
    sb = get_supabase_client()
    try:
        result = sb.table("inbox_emails").select("*").eq("id", email_id).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Email not found")

        email = result.data[0]

        def _draft():
            client = get_anthropic_client()
            prompt = (
                f"You are helping Dheeraj Reddy write a professional follow-up email.\n\n"
                f"Company: {email.get('company_name') or 'Unknown Company'}\n"
                f"Role: {email.get('role_title') or 'the position'}\n"
                f"Recruiter: {email.get('recruiter_name') or 'Hiring Manager'}\n"
                f"Original subject: {email.get('subject', '')}\n"
                f"Original email: {(email.get('body_preview') or '')[:500]}\n\n"
                "Write a concise, professional follow-up email under 150 words. "
                "Be warm but not pushy. Return ONLY the email body text."
            )
            return client.call_claude(
                model=SONNET,
                system="Write professional email follow-ups. Return only the body text.",
                user=prompt,
                max_tokens=300,
            )

        loop = asyncio.get_event_loop()
        draft_body = await loop.run_in_executor(_executor, _draft)

        return {
            "subject": f"Re: {email.get('subject', 'Following up')}",
            "body": draft_body,
            "to": email.get("sender_email", ""),
            "thread_id": email.get("thread_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SendFollowupRequest(BaseModel):
    body: str
    subject: Optional[str] = None


@router.post("/tracker/emails/{email_id}/send-followup")
async def send_followup(email_id: str, req: SendFollowupRequest):
    """Store draft_reply then send via Gmail."""
    import base64
    from email.mime.text import MIMEText
    from core.gmail_client import get_gmail_service

    sb = get_supabase_client()
    try:
        result = sb.table("inbox_emails").select("*").eq("id", email_id).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Email not found")

        email = result.data[0]

        sb.table("inbox_emails").update({
            "draft_reply": req.body,
        }).eq("id", email_id).execute()

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

        subject = req.subject or f"Re: {email.get('subject', 'Following up')}"
        msg = MIMEText(req.body)
        msg["To"] = email.get("sender_email", "")
        msg["Subject"] = subject
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
            "followup_sent": True,
        }).eq("id", email_id).execute()

        return {"message": "Follow-up sent", "email_id": email_id, "sent_at": now}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── GMAIL SYNC ───────────────────────────────────────────────────────────────

@router.post("/tracker/gmail/sync")
async def sync_gmail(background_tasks: BackgroundTasks):
    background_tasks.add_task(_do_sync)
    return {"status": "sync started"}


def _do_sync():
    import asyncio as _asyncio
    from pipelines.inbox_pipeline import run as run_inbox
    try:
        loop = _asyncio.new_event_loop()
        loop.run_until_complete(run_inbox())
        loop.close()
        logger.info("tracker.sync.complete")
    except Exception as e:
        logger.error("tracker.sync.error", error=str(e))
