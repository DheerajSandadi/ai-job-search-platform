from __future__ import annotations

import json
import base64
import structlog
from core.anthropic_client import anthropic_client, HAIKU, SONNET
from core.gmail_client import get_gmail_service_from_db as get_gmail_service
from agents.inbox.prompts import CLASSIFY_SYSTEM, CLASSIFY_USER, DRAFT_REPLY_SYSTEM, DRAFT_REPLY_USER

logger = structlog.get_logger()


def fetch_unread_emails(max_results: int = 20) -> list[dict]:
    """Fetch recent inbox emails not yet processed (no UNREAD filter)."""
    service = get_gmail_service()
    if not service:
        logger.warning("gmail_fetch_skipped", reason="not configured")
        return []

    try:
        messages_resp = service.users().messages().list(
            userId="me",
            labelIds=["INBOX"],
            maxResults=max_results,
        ).execute()
        all_ids = [m["id"] for m in messages_resp.get("messages", [])]
        logger.info("inbox_pipeline.gmail_fetched_raw", count=len(all_ids))

        if not all_ids:
            return []

        # Skip messages already stored in inbox_emails
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        already = sb.table("inbox_emails").select("id").in_(
            "id", all_ids
        ).execute()
        processed_ids = {r["id"] for r in (already.data or [])}
        new_ids = [mid for mid in all_ids if mid not in processed_ids]
        logger.info(
            "inbox_pipeline.new_emails_found",
            total=len(all_ids),
            already_processed=len(processed_ids),
            new=len(new_ids),
        )

        from datetime import datetime, timezone

        emails: list[dict] = []
        for msg_id in new_ids:
            msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            body = _extract_body(msg.get("payload", {}))
            ts = int(msg.get("internalDate", 0)) / 1000
            received_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else datetime.now(timezone.utc).isoformat()
            emails.append({
                "id": msg_id,
                "thread_id": msg.get("threadId", ""),
                "from_address": headers.get("From", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "snippet": msg.get("snippet", ""),
                "body": body,
                "labels": msg.get("labelIds", []),
                "received_at": received_at,
            })

        logger.info("gmail_fetched", count=len(emails))
        return emails
    except Exception as exc:
        logger.error("gmail_fetch_failed", error=str(exc))
        return []


def _extract_body(payload: dict) -> str:
    """Recursively extract plain-text body from Gmail message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace") if data else ""

    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text
    return ""


def classify_email(email: dict) -> dict:
    """Use Claude Haiku to classify an email."""
    try:
        raw = anthropic_client.call_claude(
            model=HAIKU,
            system=CLASSIFY_SYSTEM,
            user=CLASSIFY_USER.format(
                from_address=email.get("from_address", ""),
                subject=email.get("subject", ""),
                body=(email.get("body") or email.get("snippet", ""))[:2000],
            ),
            max_tokens=128,
        )
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        classification = result.get("classification", "unrelated")
        logger.info("email_classified", subject=email.get("subject"), classification=classification)
        return {"classification": classification, "confidence": result.get("confidence", 0.0)}
    except Exception as exc:
        logger.error("email_classify_failed", error=str(exc))
        return {"classification": "unrelated", "confidence": 0.0}


def draft_reply(email: dict) -> str | None:
    """Use Claude Sonnet to draft a reply for relevant emails."""
    classification = email.get("classification", "unrelated")
    if classification in ("unrelated",):
        return None

    try:
        reply = anthropic_client.call_claude(
            model=SONNET,
            system=DRAFT_REPLY_SYSTEM,
            user=DRAFT_REPLY_USER.format(
                from_address=email.get("from_address", ""),
                subject=email.get("subject", ""),
                body=(email.get("body") or email.get("snippet", ""))[:3000],
            ),
            max_tokens=512,
        )
        logger.info("reply_drafted", subject=email.get("subject"))
        return reply
    except Exception as exc:
        logger.error("reply_draft_failed", error=str(exc))
        return None


def mark_read(message_id: str) -> None:
    service = get_gmail_service()
    if not service:
        return
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
    except Exception as exc:
        logger.error("mark_read_failed", message_id=message_id, error=str(exc))
