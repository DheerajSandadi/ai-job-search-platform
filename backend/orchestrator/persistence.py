"""Supabase persistence for the graph nodes.

Everything here is select-then-insert-or-update — Supabase rejects
``upsert(on_conflict=...)`` with 42P10. Functions take the client so nodes
stay the single place that resolves it (and tests patch ``nodes._get_sb``).
"""
from __future__ import annotations

from datetime import datetime, timezone

import structlog

from orchestrator import registry

logger = structlog.get_logger()


def insert_discovered_jobs(sb, raw_jobs: list[dict]) -> tuple[int, int]:
    """Insert newly discovered jobs, deduplicating by URL. Returns (inserted, skipped)."""
    inserted = 0
    skipped = 0
    for job in raw_jobs:
        try:
            url = job.get("url", "")
            # Scraped URLs are untrusted: only keep http(s) links so nothing
            # downstream (browser autofill, dashboard "open job") can be
            # pointed at javascript:/file:/other schemes.
            if url and not url.lower().startswith(("http://", "https://")):
                logger.warning("persistence.bad_url_scheme", url=url[:100])
                url = ""
                job["url"] = ""
            if url:
                existing = sb.table("jobs").select("id").eq("url", url).execute()
                if existing.data:
                    skipped += 1
                    continue

            sb.table("jobs").insert({
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "description": job.get("description", ""),
                "url": url,
                "source": job.get("source", "unknown"),
                "status": "discovered",
                "raw_data": job,
            }).execute()
            inserted += 1
        except Exception as exc:
            logger.error("persistence.job_insert_error",
                         error=str(exc), job_title=job.get("title"))
            continue
    return inserted, skipped


def load_scored_jobs(sb) -> list[dict]:
    """Jobs already promoted to 'scored' in a previous run."""
    db_rows = sb.table("jobs").select("*").eq("status", "scored").execute()
    return [
        {
            "title": r["title"],
            "company": r["company"],
            "location": r.get("location", ""),
            "url": r.get("url", ""),
            "description": r.get("description", ""),
            "source": r.get("source", ""),
            "ats_score": r.get("ats_score") or 0.0,
            "relevance_score": r.get("relevance_score") or 0.0,
            "composite_score": r.get("composite_score") or 0.0,
        }
        for r in (db_rows.data or [])
    ]


def update_job_scores(sb, scored: list[dict], gate: float) -> int:
    """Write scores back to the jobs table. Returns how many passed the gate."""
    passed = 0
    for job in scored:
        cs = job.get("composite_score", 0.0)
        if cs >= gate:
            passed += 1
        try:
            url = job.get("url", "")
            if url:
                update = {
                    "ats_score": job.get("ats_score"),
                    "relevance_score": job.get("relevance_score"),
                    "composite_score": cs,
                }
                # Only promote status for qualifying jobs; low-scorers stay "discovered"
                if cs >= gate:
                    update["status"] = "scored"
                sb.table("jobs").update(update).eq("url", url).execute()
        except Exception as exc:
            logger.error("persistence.score_update_error", error=str(exc))
            continue
    return passed


def save_tailored_application(
    sb, job: dict, job_lite: dict, resume_data: dict, run_id: str
) -> tuple[dict | None, bool]:
    """Persist a tailored resume + pending application for a job.

    Returns (entry, is_pending): the state entry for the application (or None
    when the job vanished from the DB) and whether it awaits human approval.
    Registers the application → graph-thread mapping for the approval routes.
    """
    url = job.get("url", "")
    db_job = sb.table("jobs").select("id").eq("url", url).execute() if url else None
    if not db_job or not db_job.data:
        logger.warning("persistence.job_not_found", title=job.get("title"), url=url)
        return None, False

    job_id = db_job.data[0]["id"]

    # Skip if a properly tailored application already exists for this job
    existing_resume = (
        sb.table("resumes")
        .select("id, ats_score")
        .eq("job_id", job_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if existing_resume.data and (existing_resume.data[0].get("ats_score") or 0) > 0:
        logger.info("persistence.already_queued", title=job.get("title"))
        entry = {**job_lite, "resume_id": existing_resume.data[0]["id"], "job_id": job_id}
        existing_app = (
            sb.table("applications").select("id, status")
            .eq("job_id", job_id).order("created_at", desc=True).limit(1).execute()
        )
        if not existing_app.data:
            return None, False
        entry["application_id"] = existing_app.data[0]["id"]
        is_pending = existing_app.data[0].get("status") == "pending"
        if is_pending:
            registry.register_application_thread(entry["application_id"], run_id)
        return entry, is_pending

    # Clean up any failed/fallback resume so we can re-insert a good one
    if existing_resume.data:
        rid = existing_resume.data[0]["id"]
        sb.table("applications").delete().eq("job_id", job_id).eq("status", "pending").execute()
        sb.table("resumes").delete().eq("id", rid).execute()

    resume_row = sb.table("resumes").insert({
        "job_id": job_id,
        "original_text": resume_data.get("original_text", ""),
        "tailored_text": resume_data.get("tailored_text", ""),
        "diff_summary": resume_data.get("diff_summary", ""),
        "ats_score": resume_data.get("ats_score"),
        "keywords_added": resume_data.get("keywords_added", []),
    }).execute()
    resume_id = resume_row.data[0]["id"]

    app_row = sb.table("applications").insert({
        "job_id": job_id,
        "resume_id": resume_id,
        "status": "pending",
    }).execute()
    application_id = app_row.data[0]["id"]

    sb.table("jobs").update({"status": "pending_approval"}).eq("id", job_id).execute()

    # Record which graph thread owns this application so the
    # approve/reject/mark-applied routes can resume it later.
    registry.register_application_thread(application_id, run_id)

    entry = {**job_lite, "resume_id": resume_id,
             "job_id": job_id, "application_id": application_id}
    return entry, True


def save_recruiters(sb, batches: list[dict]) -> tuple[list[dict], list[dict]]:
    """Dedupe-insert recruiters. Returns (flat recruiters, batches that had any)."""
    all_recruiters: list[dict] = []
    kept_batches: list[dict] = []

    for batch in batches:
        job = batch.get("job", {})
        recruiters = batch.get("recruiters", [])
        if not recruiters:
            continue

        for rec in recruiters:
            try:
                email = rec.get("email")
                if email:
                    existing = (
                        sb.table("recruiters").select("id").eq("email", email)
                        .limit(1).execute()
                    )
                    if existing.data:
                        all_recruiters.append({**rec, "_job": job})
                        continue
                sb.table("recruiters").insert({
                    "name": rec.get("name") or rec.get("full_name", ""),
                    "title": rec.get("title", ""),
                    "company": rec.get("company", ""),
                    "email": email,
                    "linkedin_url": rec.get("linkedin_url"),
                    "source": "apollo",
                }).execute()
                all_recruiters.append({**rec, "_job": job})
            except Exception as exc:
                logger.error("persistence.recruiter_insert_error", error=str(exc))
                continue

        kept_batches.append(batch)

    return all_recruiters, kept_batches


def save_outreach_draft(sb, record: dict) -> str | None:
    """Insert a queued outreach row for a drafted email; returns its id."""
    recruiter = record.get("recruiter", {})
    job = record.get("job", {})

    recruiter_db_id = None
    email = recruiter.get("email", "")
    if email:
        db_rec = (
            sb.table("recruiters").select("id").eq("email", email)
            .order("created_at", desc=True).limit(1).execute()
        )
        recruiter_db_id = db_rec.data[0]["id"] if db_rec.data else None

    if not recruiter_db_id:
        logger.warning("persistence.no_recruiter_id", email=email)
        return None

    job_db_id = job.get("job_id")
    if not job_db_id:
        url = job.get("url", "")
        if url:
            db_job = sb.table("jobs").select("id").eq("url", url).execute()
            job_db_id = db_job.data[0]["id"] if db_job.data else None

    try:
        row = sb.table("outreach").insert({
            "recruiter_id": recruiter_db_id,
            "job_id": job_db_id,
            "channel": "email",
            "subject": record.get("subject"),
            "body": record.get("body", ""),
            "status": "queued",
        }).execute()
        return row.data[0]["id"] if row.data else None
    except Exception as exc:
        logger.error("persistence.outreach_insert_error", error=str(exc))
        return None


def mark_outreach_sent(sb, outreach_id: str) -> None:
    try:
        sb.table("outreach").update({
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", outreach_id).execute()
    except Exception as exc:
        logger.error("persistence.outreach_update_error", error=str(exc))


def write_analytics(sb, today: str, analytics_row: dict,
                    is_discovery_run: bool, newly_sent: int) -> None:
    """Insert today's analytics row, or update only pipeline-owned fields.

    applications_submitted is incremented by mark-applied clicks and
    recruiter_replies / interviews_scheduled by the inbox flow — clobbering
    them here would reset the user's counters. Follow-on outreach runs have no
    raw_jobs and must not zero out the morning discovery numbers either;
    recruiters_contacted accumulates across the day's runs.
    """
    existing = sb.table("analytics").select("id, recruiters_contacted").eq("date", today).execute()
    if existing.data:
        update: dict = {}
        if is_discovery_run:
            update["jobs_discovered"] = analytics_row["jobs_discovered"]
            update["jobs_scored"] = analytics_row["jobs_scored"]
        if newly_sent:
            current = existing.data[0].get("recruiters_contacted") or 0
            update["recruiters_contacted"] = current + newly_sent
        if update:
            sb.table("analytics").update(update).eq("date", today).execute()
    else:
        sb.table("analytics").insert({"date": today, **analytics_row}).execute()
