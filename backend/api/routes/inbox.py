from fastapi import APIRouter, HTTPException, Query
from models.schemas import InboxEmail, EmailClassification
from core.supabase_client import get_supabase_client
import structlog

router = APIRouter(prefix="/inbox", tags=["inbox"])
logger = structlog.get_logger()


@router.get("", response_model=list[InboxEmail])
async def list_inbox(
    classification: EmailClassification | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[InboxEmail]:
    try:
        sb = get_supabase_client()
        if sb is None:
            raise HTTPException(status_code=503, detail="Database not configured")
        query = sb.table("inbox_emails").select("*")
        if classification:
            query = query.eq("classification", classification.value)
        query = query.order("received_at", desc=True)
        query = query.range((page - 1) * page_size, page * page_size - 1)
        result = query.execute()
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_inbox_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
