from __future__ import annotations

import structlog
from agents.inbox.tools import fetch_unread_emails, classify_email, draft_reply, mark_read
from core.supabase_client import get_supabase_client

logger = structlog.get_logger()


ACTIONABLE = {"recruiter_reply", "interview_invite", "offer", "follow_up_needed"}


def run(mark_as_read: bool = True) -> list[dict]:
    """
    Fetch inbox emails, classify them, draft replies for actionable ones,
    and persist all results to inbox_emails.
    """
    logger.info("inbox_agent_started")
    emails = fetch_unread_emails()

    if not emails:
        logger.info("inbox_agent_no_emails")
        return []

    sb = get_supabase_client()
    results: list[dict] = []

    for email in emails:
        clf = classify_email(email)
        email["classification"] = clf["classification"]
        email["confidence"] = clf["confidence"]

        if clf["classification"] in ACTIONABLE:
            email["draft_reply"] = draft_reply(email)
        else:
            email["draft_reply"] = None

        if mark_as_read and clf["classification"] != "unrelated":
            mark_read(email["id"])

        try:
            sb.table("inbox_emails").upsert({
                "id":               email["id"],
                "gmail_message_id": email["id"],
                "thread_id":        email.get("thread_id"),
                "sender_email":     email.get("sender_email") or email.get("from_address", ""),
                "sender_name":      email.get("sender_name"),
                "subject":          email.get("subject"),
                "body_preview":     (email.get("body_preview") or email.get("snippet") or "")[:500],
                "full_body":        email.get("full_body") or email.get("body"),
                "received_at":      email["received_at"],
                "classification":   email["classification"],
                "pipeline_stage":   email.get("pipeline_stage") or email.get("classification", "classified"),
                "draft_reply":      email.get("draft_reply"),
                "company_name":     email.get("company_name"),
                "role_title":       email.get("role_title"),
                "reply_sent":       False,
                "labels":           email.get("labels", []),
            }, on_conflict="id").execute()
        except Exception as exc:
            logger.error("inbox_persist_failed", msg_id=email["id"], error=str(exc))

        results.append(email)
        logger.info(
            "inbox_processed",
            subject=email.get("subject"),
            classification=clf["classification"],
            has_draft=bool(email.get("draft_reply")),
        )

    logger.info(
        "inbox_agent_complete",
        total=len(results),
        actionable=sum(1 for e in results if e.get("classification") in ACTIONABLE),
    )
    return results
