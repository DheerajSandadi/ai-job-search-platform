from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from models.schemas import Settings
from core.config import settings as app_config
from core.supabase_client import get_supabase_client
import structlog

router = APIRouter(prefix="/settings", tags=["settings"])
logger = structlog.get_logger()

_COMPUTED_FIELDS = {"anthropic_key_configured", "supabase_configured", "gmail_configured"}


def _runtime_flags(stored: dict | None = None) -> dict:
    return {
        "anthropic_key_configured": bool(app_config.ANTHROPIC_API_KEY),
        "supabase_configured": bool(app_config.SUPABASE_URL and app_config.SUPABASE_SERVICE_ROLE_KEY),
        "gmail_configured": bool((stored or {}).get("gmail_refresh_token")),
    }


def _config_defaults() -> dict:
    return {
        "ats_confidence_threshold": app_config.ATS_CONFIDENCE_THRESHOLD,
        "morning_pipeline_cron": app_config.MORNING_PIPELINE_CRON,
        "retry_pipeline_cron": app_config.RETRY_PIPELINE_CRON,
        "auto_apply_enabled": False,
        "max_applications_per_day": 20,
        "target_roles": [],
        "excluded_companies": [],
    }


@router.get("", response_model=Settings)
async def get_settings() -> Settings:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        result = sb.table("settings").select("*").limit(1).execute()
        stored = result.data[0] if result.data else _config_defaults()
        return Settings(**{**stored, **_runtime_flags(stored)})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_settings_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("", response_model=Settings)
async def update_settings(body: Settings) -> Settings:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        payload = body.model_dump(exclude=_COMPUTED_FIELDS)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()

        existing = sb.table("settings").select("id, gmail_refresh_token").limit(1).execute()
        if existing.data:
            sb.table("settings").update(payload).eq("id", existing.data[0]["id"]).execute()
            stored_row = existing.data[0]
        else:
            sb.table("settings").insert(payload).execute()
            stored_row = {}

        logger.info("settings_updated")
        return Settings(**{**payload, **_runtime_flags(stored_row)})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_settings_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
