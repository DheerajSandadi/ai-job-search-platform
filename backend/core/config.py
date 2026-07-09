from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    ANTHROPIC_API_KEY: str = ""

    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REDIRECT_URI: str = "http://localhost:8001/auth/gmail/callback"
    GMAIL_USER_EMAIL: str = ""

    APOLLO_API_KEY: str = ""
    APIFY_API_KEY: str = ""
    VIBE_PROSPECTING_API_KEY: str = ""

    GOOGLE_CLOUD_PROJECT_ID: str = ""
    PUBSUB_TOPIC_NAME: str = "gmail-push"

    DASHBOARD_USERNAME: str = "admin"
    DASHBOARD_PASSWORD: str = "changeme"

    # Optional API protection. When API_KEY is set, /api/v1/* requires the
    # X-API-Key header. Empty (default) keeps the local MVP flow open.
    API_KEY: str = ""
    # Optional shared secret for the Gmail Pub/Sub push endpoint. When set,
    # /webhooks/gmail requires ?token=<value> (configure the same token on the
    # Pub/Sub push subscription URL).
    PUBSUB_VERIFICATION_TOKEN: str = ""

    ATS_CONFIDENCE_THRESHOLD: float = 0.8
    MORNING_PIPELINE_CRON: str = "0 6 * * *"
    RETRY_PIPELINE_CRON: str = "0 9 * * *"

    # LangGraph orchestration — local sqlite persistence for interrupted runs
    ORCHESTRATOR_CHECKPOINT_DB: str = "data/orchestrator_checkpoints.sqlite"
    ORCHESTRATOR_REGISTRY_DB: str = "data/approval_threads.sqlite"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def get_settings() -> Settings:
    return settings
