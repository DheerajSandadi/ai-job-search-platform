from functools import lru_cache
from supabase import create_client, Client
from core.config import settings
import structlog

logger = structlog.get_logger()


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("supabase_not_configured", msg="SUPABASE_URL or key missing — client disabled")
        return None  # type: ignore[return-value]
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    logger.info("supabase_client_created", url=settings.SUPABASE_URL)
    return client


supabase: Client = get_supabase_client()
