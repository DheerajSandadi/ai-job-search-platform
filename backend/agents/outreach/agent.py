from __future__ import annotations

import structlog
from agents.outreach.tools import draft_email, send_email

logger = structlog.get_logger()


def run(recruiter_results: list[dict], dry_run: bool = False) -> list[dict]:
    """
    Draft and optionally send outreach emails to recruiters.

    Args:
        recruiter_results: list of {"job": {...}, "recruiters": [{...}]}
        dry_run: if True, draft emails but do not send

    Returns list of outreach records with status.
    """
    logger.info("outreach_agent_started", batches=len(recruiter_results), dry_run=dry_run)
    sent: list[dict] = []

    for item in recruiter_results:
        job = item.get("job", {})
        recruiters = item.get("recruiters", [])

        for recruiter in recruiters:
            email_data = draft_email(recruiter, job)
            to_addr = recruiter.get("email")

            record = {
                "recruiter": recruiter,
                "job": job,
                "subject": email_data["subject"],
                "body": email_data["body"],
                "sent": False,
                "dry_run": dry_run,
            }

            if to_addr and not dry_run:
                success = send_email(to_addr, email_data["subject"], email_data["body"])
                record["sent"] = success
            elif dry_run:
                logger.info("outreach_dry_run", recruiter=recruiter.get("name"), company=job.get("company"))

            sent.append(record)

    logger.info("outreach_agent_complete", total=len(sent), sent=sum(1 for r in sent if r["sent"]))
    return sent
