from __future__ import annotations

import structlog
from core.gmail_client import get_gmail_service_from_db as get_gmail_service
from core.config import get_settings

logger = structlog.get_logger()


def setup_push_notifications() -> dict | None:
    """Configure Gmail push notifications to a Google Cloud Pub/Sub topic."""
    settings = get_settings()
    topic_name = f"projects/{settings.GOOGLE_CLOUD_PROJECT_ID}/topics/{settings.PUBSUB_TOPIC_NAME}"

    service = get_gmail_service()
    if not service:
        logger.warning("gmail_pubsub_skipped", reason="gmail service not configured")
        return None

    try:
        result = service.users().watch(
            userId="me",
            body={
                "topicName": topic_name,
                "labelIds": ["INBOX"],
                "labelFilterAction": "include",
            },
        ).execute()
        logger.info("gmail_push_setup", expiry=result.get("expiration"), history_id=result.get("historyId"))
        return result
    except Exception as exc:
        logger.error("gmail_push_setup_failed", error=str(exc))
        return None


def stop_push_notifications() -> None:
    service = get_gmail_service()
    if not service:
        return
    try:
        service.users().stop(userId="me").execute()
        logger.info("gmail_push_stopped")
    except Exception as exc:
        logger.error("gmail_push_stop_failed", error=str(exc))
