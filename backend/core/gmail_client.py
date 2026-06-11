from __future__ import annotations

import structlog
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from core.config import settings as _settings

logger = structlog.get_logger()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]

_gmail_service = None
_credentials: Credentials | None = None


def get_oauth_flow() -> Flow:
    """Build OAuth flow from env vars — no credentials.json needed."""
    client_config = {
        "web": {
            "client_id": _settings.GMAIL_CLIENT_ID,
            "client_secret": _settings.GMAIL_CLIENT_SECRET,
            "redirect_uris": [_settings.GMAIL_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=_settings.GMAIL_REDIRECT_URI,
    )


def get_gmail_service(access_token: str | None = None, refresh_token: str | None = None):
    """Return Gmail API service built from the provided tokens."""
    global _gmail_service, _credentials

    if _gmail_service and _credentials and _credentials.valid:
        return _gmail_service

    if not access_token or not refresh_token:
        logger.warning("gmail.no_tokens", msg="No tokens provided — Gmail not available")
        return None

    _credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_settings.GMAIL_CLIENT_ID,
        client_secret=_settings.GMAIL_CLIENT_SECRET,
        scopes=SCOPES,
    )

    if _credentials.expired and _credentials.refresh_token:
        try:
            _credentials.refresh(Request())
            logger.info("gmail.token_refreshed")
        except Exception as e:
            logger.error("gmail.refresh_failed", error=str(e))
            return None

    _gmail_service = build("gmail", "v1", credentials=_credentials)
    logger.info("gmail.service_ready", user=_settings.GMAIL_USER_EMAIL)
    return _gmail_service


def get_gmail_service_from_db():
    """Load OAuth tokens from Supabase settings and return Gmail service."""
    from core.supabase_client import get_supabase_client
    sb = get_supabase_client()
    if sb is None:
        logger.warning("gmail.supabase_not_configured")
        return None
    try:
        result = sb.table("settings").select("gmail_access_token, gmail_refresh_token").limit(1).execute()
    except Exception as e:
        logger.error("gmail.settings_fetch_failed", error=str(e))
        return None

    if not result.data:
        logger.warning("gmail.no_settings")
        return None

    row = result.data[0]
    refresh_token = row.get("gmail_refresh_token")
    if not refresh_token:
        logger.warning("gmail.not_connected")
        return None

    return get_gmail_service(
        access_token=row.get("gmail_access_token"),
        refresh_token=refresh_token,
    )
