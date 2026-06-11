from __future__ import annotations

import json
import base64
import email as email_lib
import structlog
from email.mime.text import MIMEText
from core.anthropic_client import anthropic_client, SONNET
from core.gmail_client import get_gmail_service_from_db as get_gmail_service
from agents.outreach.prompts import DRAFT_SYSTEM, DRAFT_USER

logger = structlog.get_logger()

SENDER_EMAIL = "dheerajreddysandadi@icloud.com"


def draft_email(
    recruiter: dict,
    job: dict,
    company_context: str = "",
) -> dict:
    """Use Claude Sonnet to draft a personalized outreach email."""
    try:
        user_msg = DRAFT_USER.format(
            recruiter_name=recruiter.get("name", "Hiring Team"),
            recruiter_title=recruiter.get("title", "Recruiter"),
            company=job.get("company", ""),
            role_title=job.get("title", ""),
            company_context=company_context or f"I've been following {job.get('company', 'your company')} and am excited by your work in AI/ML.",
        )
        raw = anthropic_client.call_claude(
            model=SONNET,
            system=DRAFT_SYSTEM,
            user=user_msg,
            max_tokens=512,
        )
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        logger.info("email_drafted", recruiter=recruiter.get("name"), company=job.get("company"))
        return {"subject": result.get("subject", ""), "body": result.get("body", "")}
    except Exception as exc:
        logger.error("email_draft_failed", error=str(exc))
        return {
            "subject": f"Interested in {job.get('title', 'engineering roles')} at {job.get('company', 'your company')}",
            "body": f"Hi {recruiter.get('name', 'there')},\n\nI'm Dheeraj Reddy, a software engineer with experience in Python, ML/AI, and full-stack development. I'd love to learn more about opportunities at {job.get('company', 'your company')}.\n\nWould you have 15 minutes for a quick call?\n\nBest,\nDheeraj",
        }


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Send an email via the Gmail API."""
    service = get_gmail_service()
    if not service:
        logger.warning("gmail_send_skipped", reason="gmail not configured")
        return False

    try:
        message = MIMEText(body, "plain")
        message["to"] = to_address
        message["from"] = SENDER_EMAIL
        message["subject"] = subject
        raw_bytes = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        service.users().messages().send(
            userId="me",
            body={"raw": raw_bytes},
        ).execute()
        logger.info("email_sent", to=to_address, subject=subject)
        return True
    except Exception as exc:
        logger.error("email_send_failed", to=to_address, error=str(exc))
        return False
