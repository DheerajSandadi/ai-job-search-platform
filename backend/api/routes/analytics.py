from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Query
from models.schemas import AnalyticsDay
from core.supabase_client import get_supabase_client
import structlog

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = structlog.get_logger()

_ZERO_DAY = {
    "jobs_discovered": 0,
    "jobs_scored": 0,
    "applications_submitted": 0,
    "applications_failed": 0,
    "recruiters_contacted": 0,
    "recruiter_replies": 0,
    "interviews_scheduled": 0,
}


@router.get("/today", response_model=AnalyticsDay)
async def get_today_analytics() -> AnalyticsDay:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        today = date.today().isoformat()
        result = sb.table("analytics").select("*").eq("date", today).limit(1).execute()
        if not result.data:
            return AnalyticsDay(date=today, **_ZERO_DAY)
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_today_analytics_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=list[AnalyticsDay])
async def get_analytics_history(days: int = Query(7, ge=1, le=90)) -> list[AnalyticsDay]:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        from_date = (date.today() - timedelta(days=days)).isoformat()
        result = (
            sb.table("analytics")
            .select("*")
            .gte("date", from_date)
            .order("date", desc=False)
            .execute()
        )
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_analytics_history_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
