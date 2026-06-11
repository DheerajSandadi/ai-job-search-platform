from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from api.routes import jobs, applications, outreach, inbox, analytics, pipelines, settings
from api.routes.auth import router as auth_router
from scheduler.jobs import start_scheduler, stop_scheduler

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", msg="AI Job Search Platform starting up")
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("shutdown", msg="AI Job Search Platform shut down")


app = FastAPI(
    title="AI Job Search Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"
app.include_router(jobs.router,         prefix=PREFIX)
app.include_router(applications.router, prefix=PREFIX)
app.include_router(outreach.router,     prefix=PREFIX)
app.include_router(inbox.router,        prefix=PREFIX)
app.include_router(analytics.router,    prefix=PREFIX)
app.include_router(pipelines.router,    prefix=PREFIX)
app.include_router(settings.router,     prefix=PREFIX)
app.include_router(auth_router)


@app.get("/health")
async def health() -> dict:
    from core.config import settings as app_config
    from core.supabase_client import get_supabase_client

    sb_status = "connected"
    try:
        sb = get_supabase_client()
        if sb is None:
            sb_status = "not_configured"
        else:
            sb.table("jobs").select("id").limit(1).execute()
    except Exception:
        sb_status = "error"

    return {
        "status": "healthy",
        "supabase": sb_status,
        "anthropic": "configured" if app_config.ANTHROPIC_API_KEY else "missing",
        "gmail": "configured" if app_config.GMAIL_CLIENT_ID else "missing",
        "apify": "configured" if app_config.APIFY_API_KEY else "missing",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/webhooks/gmail")
async def gmail_webhook(request: Request) -> JSONResponse:
    payload = await request.json()
    logger.info("gmail_webhook_received", payload=payload)

    import asyncio
    from api.routes.pipelines import _execute_pipeline
    from core.supabase_client import get_supabase_client

    sb = get_supabase_client()
    if sb:
        try:
            inserted = sb.table("pipeline_runs").insert({
                "pipeline_type": "inbox",
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            run_id = inserted.data[0]["id"]
            asyncio.create_task(_execute_pipeline("inbox", run_id))
        except Exception as e:
            logger.error("gmail_webhook_trigger_failed", error=str(e))

    return JSONResponse({"status": "accepted"})
