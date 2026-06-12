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

    GOOGLE_CLOUD_PROJECT_ID: str = ""
    PUBSUB_TOPIC_NAME: str = "gmail-push"

    DASHBOARD_USERNAME: str = "admin"
    DASHBOARD_PASSWORD: str = "changeme"

    ATS_CONFIDENCE_THRESHOLD: float = 0.8
    MORNING_PIPELINE_CRON: str = "0 6 * * *"
    RETRY_PIPELINE_CRON: str = "0 9 * * *"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def get_settings() -> Settings:
    return settings
