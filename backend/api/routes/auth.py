from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from core.gmail_client import get_oauth_flow
from core.config import settings as app_config
from core.supabase_client import get_supabase_client
from integrations.gmail.pubsub import setup_push_notifications
import structlog

router = APIRouter(prefix="/auth", tags=["auth"])
logger = structlog.get_logger()


@router.get("/gmail/login")
async def gmail_login():
    """Redirect browser to Google OAuth consent screen."""
    if not app_config.GMAIL_CLIENT_ID or not app_config.GMAIL_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET not configured")
    flow = get_oauth_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )
    return RedirectResponse(auth_url)


@router.get("/gmail/callback")
async def gmail_callback(code: str, state: str | None = None):
    """Exchange auth code for tokens and persist them to Supabase settings."""
    try:
        flow = get_oauth_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
    except Exception as e:
        logger.error("gmail.oauth_callback_failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {e}")

    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")

        token_payload = {
            "gmail_access_token": credentials.token,
            "gmail_refresh_token": credentials.refresh_token,
        }
        existing = sb.table("settings").select("id").limit(1).execute()
        if existing.data:
            sb.table("settings").update(token_payload).eq("id", existing.data[0]["id"]).execute()
        else:
            sb.table("settings").insert(token_payload).execute()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("gmail.token_save_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to save tokens: {e}")

    logger.info("gmail.connected", user=app_config.GMAIL_USER_EMAIL)
    return {"message": "Gmail connected successfully", "email": app_config.GMAIL_USER_EMAIL}


@router.get("/gmail/status")
async def gmail_status():
    """Return whether Gmail tokens are stored."""
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        result = sb.table("settings").select("gmail_refresh_token").limit(1).execute()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("gmail.status_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    connected = bool(result.data and result.data[0].get("gmail_refresh_token"))
    return {"connected": connected, "email": app_config.GMAIL_USER_EMAIL if connected else None}


@router.post("/gmail/watch")
async def gmail_watch():
    """Start Gmail push notifications via Pub/Sub watch."""
    details = setup_push_notifications()
    if details is None:
        raise HTTPException(status_code=503, detail="Gmail not configured or watch call failed")
    return {"status": "watching", "details": details}
