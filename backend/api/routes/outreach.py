from fastapi import APIRouter, HTTPException, Query
from models.schemas import Outreach, OutreachChannel, OutreachStatus
from core.supabase_client import get_supabase_client
import structlog

router = APIRouter(prefix="/outreach", tags=["outreach"])
logger = structlog.get_logger()


@router.get("", response_model=list[Outreach])
async def list_outreach(
    status: OutreachStatus | None = Query(None),
    channel: OutreachChannel | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[Outreach]:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        query = sb.table("outreach").select("*, recruiters(*)")
        if status:
            query = query.eq("status", status.value)
        if channel:
            query = query.eq("channel", channel.value)
        query = query.order("created_at", desc=True)
        query = query.range((page - 1) * page_size, page * page_size - 1)
        result = query.execute()
        for row in result.data:
            row["recruiter"] = row.pop("recruiters", None)
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_outreach_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
