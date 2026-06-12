from contextlib import asynccontextmanager
from datetime import datetime, timezone
import secrets
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import structlog

from api.routes import jobs, applications, outreach, inbox, analytics, pipelines, settings
from api.routes.auth import router as auth_router
from api.routes.tracker import router as tracker_router
from scheduler.jobs import start_scheduler, stop_scheduler

logger = structlog.get_logger()

_http_security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(_http_security)) -> str:
    from core.config import get_settings
    cfg = get_settings()
    correct_user = secrets.compare_digest(
        credentials.username.encode("utf8"),
        (cfg.DASHBOARD_USERNAME or "admin").encode("utf8"),
    )
    correct_pass = secrets.compare_digest(
        credentials.password.encode("utf8"),
        (cfg.DASHBOARD_PASSWORD or "jobpilot").encode("utf8"),
    )
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=401,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


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
_auth = [Depends(verify_credentials)]
app.include_router(jobs.router,         prefix=PREFIX, dependencies=_auth)
app.include_router(applications.router, prefix=PREFIX, dependencies=_auth)
app.include_router(outreach.router,     prefix=PREFIX, dependencies=_auth)
app.include_router(inbox.router,        prefix=PREFIX, dependencies=_auth)
app.include_router(analytics.router,    prefix=PREFIX, dependencies=_auth)
app.include_router(pipelines.router,    prefix=PREFIX, dependencies=_auth)
app.include_router(settings.router,     prefix=PREFIX, dependencies=_auth)
app.include_router(tracker_router,      prefix=PREFIX, dependencies=_auth)
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
