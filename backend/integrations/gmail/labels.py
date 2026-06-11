from __future__ import annotations

import structlog
from core.gmail_client import get_gmail_service_from_db as get_gmail_service

logger = structlog.get_logger()

LABEL_JOBPILOT = "JobPilot"
LABEL_APPLIED = "JobPilot/Applied"
LABEL_REPLY = "JobPilot/RecruiterReply"
LABEL_INTERVIEW = "JobPilot/Interview"
LABEL_REJECTION = "JobPilot/Rejection"

_LABEL_NAMES = [LABEL_JOBPILOT, LABEL_APPLIED, LABEL_REPLY, LABEL_INTERVIEW, LABEL_REJECTION]


def ensure_labels() -> dict[str, str]:
    """Create JobPilot labels if missing. Returns name→id mapping."""
    service = get_gmail_service()
    if not service:
        return {}

    existing = {l["name"]: l["id"] for l in service.users().labels().list(userId="me").execute().get("labels", [])}
    label_ids: dict[str, str] = {}

    for name in _LABEL_NAMES:
        if name in existing:
            label_ids[name] = existing[name]
        else:
            try:
                result = service.users().labels().create(
                    userId="me",
                    body={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
                ).execute()
                label_ids[name] = result["id"]
                logger.info("gmail_label_created", name=name)
            except Exception as exc:
                logger.error("gmail_label_create_failed", name=name, error=str(exc))

    return label_ids


def apply_label(message_id: str, label_name: str, label_ids: dict[str, str]) -> None:
    service = get_gmail_service()
    if not service or label_name not in label_ids:
        return
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_ids[label_name]]},
        ).execute()
        logger.info("gmail_label_applied", message_id=message_id, label=label_name)
    except Exception as exc:
        logger.error("gmail_label_apply_failed", message_id=message_id, error=str(exc))
