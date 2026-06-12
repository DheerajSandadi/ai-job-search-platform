from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import structlog

from orchestrator.state import PipelineState
from agents.job_scout.tools import search_jobs, score_job
from agents.job_scout.agent import DEFAULT_QUERIES
from agents.resume import agent as resume_agent
from agents.recruiter import agent as recruiter_agent
from agents.outreach import agent as outreach_agent
from core.config import settings
from core.supabase_client import get_supabase_client

logger = structlog.get_logger()

_executor = ThreadPoolExecutor(max_workers=4)
_SCORE_THRESHOLD = 0.65


def _get_sb():
    return get_supabase_client()


async def _run_in_thread(fn):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, fn)


# ─── Step 1: discover jobs and write to DB ───────────────────────────────────

async def discover_jobs_node(state: PipelineState) -> PipelineState:
    logger.info("node.discover_jobs.start")
    try:
        raw_jobs = await _run_in_thread(
            lambda: search_jobs(DEFAULT_QUERIES, location="Remote", max_per_query=15)
        )
        state["raw_jobs"] = raw_jobs or []

        if not raw_jobs:
            logger.warning("node.discover_jobs.empty")
            return state

        sb = _get_sb()
        inserted = 0
        skipped = 0

        for job in raw_jobs:
            try:
                url = job.get("url", "")
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
                logger.error("node.discover_jobs.insert_error",
                             error=str(exc), job_title=job.get("title"))
                continue

        logger.info("node.discover_jobs.done",
                    total=len(raw_jobs), inserted=inserted, skipped=skipped)

    except Exception as exc:
        logger.error("node.discover_jobs.error", error=str(exc))
        state.setdefault("errors", []).append(f"discover_jobs: {exc}")
        state["raw_jobs"] = []

    return state


# ─── Step 2: score all discovered jobs and update DB ─────────────────────────

async def score_jobs_node(state: PipelineState) -> PipelineState:
    raw_jobs = state.get("raw_jobs", [])
    logger.info("node.score_jobs.start", count=len(raw_jobs))

    if not raw_jobs:
        # No new jobs this run — load already-scored jobs from DB for downstream stages
        sb = _get_sb()
        db_rows = sb.table("jobs").select("*").eq("status", "scored").execute()
        if db_rows.data:
            state["scored_jobs"] = [
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
                for r in db_rows.data
            ]
            logger.info("node.score_jobs.loaded_from_db", count=len(db_rows.data))
        else:
            state["scored_jobs"] = []
        return state

    try:
        scored = await _run_in_thread(lambda: [score_job(j) for j in raw_jobs])
        state["scored_jobs"] = scored or []

        sb = _get_sb()
        passed = 0
        skipped_count = 0

        for job in scored:
            cs = job.get("composite_score", 0.0)
            if cs >= _SCORE_THRESHOLD:
                passed += 1
            else:
                skipped_count += 1

            try:
                url = job.get("url", "")
                if url:
                    update = {
                        "ats_score": job.get("ats_score"),
                        "relevance_score": job.get("relevance_score"),
                        "composite_score": cs,
                    }
                    # Only promote status for qualifying jobs; low-scorers stay "discovered"
                    if cs >= _SCORE_THRESHOLD:
                        update["status"] = "scored"
                    sb.table("jobs").update(update).eq("url", url).execute()
            except Exception as exc:
                logger.error("node.score_jobs.update_error", error=str(exc))
                continue

        logger.info("node.score_jobs.done", passed=passed, skipped=skipped_count)

    except Exception as exc:
        logger.error("node.score_jobs.error", error=str(exc))
        state.setdefault("errors", []).append(f"score_jobs: {exc}")
        state["scored_jobs"] = raw_jobs  # fall back to unscored if whole step fails

    return state


# ─── Step 3: tailor resumes for qualifying jobs, create pending applications ──

async def tailor_resume_node(state: PipelineState) -> PipelineState:
    scored = state.get("scored_jobs", [])
    high_score = [j for j in scored if j.get("composite_score", 0.0) >= _SCORE_THRESHOLD]

    logger.info("node.tailor_resume.start",
                scored=len(scored), qualifying=len(high_score))

    state["tailored_resumes"] = []
    state["pending_approvals"] = []

    if not high_score:
        return state

    sb = _get_sb()
    tailored: list[dict] = []

    for job in high_score:
        try:
            result = await _run_in_thread(lambda j=job: resume_agent.run([j]))
            if not result:
                continue
            resume_data = result[0].get("resume", {})

            url = job.get("url", "")
            db_job = sb.table("jobs").select("id").eq("url", url).execute() if url else None
            if not db_job or not db_job.data:
                logger.warning("node.tailor_resume.job_not_found",
                               title=job.get("title"), url=url)
                continue

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
                logger.info("node.tailor_resume.already_queued", title=job.get("title"))
                tailored.append({**job, "resume_id": existing_resume.data[0]["id"], "job_id": job_id})
                continue
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

            sb.table("applications").insert({
                "job_id": job_id,
                "resume_id": resume_id,
                "status": "pending",
            }).execute()

            sb.table("jobs").update({"status": "pending_approval"}).eq("id", job_id).execute()

            tailored.append({**job, "resume_id": resume_id, "job_id": job_id})
            logger.info("node.tailor_resume.queued",
                        title=job.get("title"), ats_score=resume_data.get("ats_score"))

        except Exception as exc:
            logger.error("node.tailor_resume.error",
                         error=str(exc), job_title=job.get("title"))
            continue

    state["tailored_resumes"] = tailored
    state["pending_approvals"] = tailored
    logger.info("node.tailor_resume.done", queued=len(tailored))
    return state


# ─── Step 4: find recruiters and write to DB ─────────────────────────────────

async def find_recruiters_node(state: PipelineState) -> PipelineState:
    # Use tailored jobs; fall back to top scored jobs when AUTO_APPLY_ENABLED=False
    jobs_for_recruiting = state.get("tailored_resumes") or [
        j for j in state.get("scored_jobs", [])
        if j.get("composite_score", 0.0) >= _SCORE_THRESHOLD
    ]
    logger.info("node.find_recruiters.start", jobs=len(jobs_for_recruiting))

    state["recruiters"] = []
    state["outreach_queue"] = []

    if not jobs_for_recruiting:
        return state

    sb = _get_sb()
    all_recruiters: list[dict] = []
    outreach_batches: list[dict] = []

    try:
        recruiter_results = await _run_in_thread(
            lambda: recruiter_agent.run(jobs_for_recruiting)
        )

        for batch in (recruiter_results or []):
            job = batch.get("job", {})
            recruiters = batch.get("recruiters", [])

            if not recruiters:
                continue

            for rec in recruiters:
                try:
                    sb.table("recruiters").insert({
                        "name": rec.get("name") or rec.get("full_name", ""),
                        "title": rec.get("title", ""),
                        "company": rec.get("company", ""),
                        "email": rec.get("email"),
                        "linkedin_url": rec.get("linkedin_url"),
                        "source": "apollo",
                    }).execute()
                    all_recruiters.append({**rec, "_job": job})
                except Exception as exc:
                    logger.error("node.find_recruiters.insert_error", error=str(exc))
                    continue

            outreach_batches.append(batch)

    except Exception as exc:
        logger.error("node.find_recruiters.error", error=str(exc))
        state.setdefault("errors", []).append(f"recruiters: {exc}")

    state["recruiters"] = all_recruiters
    state["outreach_queue"] = outreach_batches
    logger.info("node.find_recruiters.done", count=len(all_recruiters))
    return state


# ─── Step 5: generate outreach emails and write to DB ────────────────────────

async def generate_outreach_node(state: PipelineState) -> PipelineState:
    queue = state.get("outreach_queue", [])
    logger.info("node.generate_outreach.start", batches=len(queue))

    state["outreach_sent"] = []

    if not queue:
        return state

    sb = _get_sb()
    sent: list[dict] = []

    try:
        outreach_results = await _run_in_thread(
            lambda: outreach_agent.run(queue, dry_run=False)
        )

        for record in (outreach_results or []):
            recruiter = record.get("recruiter", {})
            job = record.get("job", {})

            # Resolve recruiter DB id by email
            recruiter_db_id = None
            email = recruiter.get("email", "")
            if email:
                db_rec = (
                    sb.table("recruiters")
                    .select("id")
                    .eq("email", email)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                recruiter_db_id = db_rec.data[0]["id"] if db_rec.data else None

            # Resolve job DB id
            job_db_id = job.get("job_id")
            if not job_db_id:
                url = job.get("url", "")
                if url:
                    db_job = sb.table("jobs").select("id").eq("url", url).execute()
                    job_db_id = db_job.data[0]["id"] if db_job.data else None

            if not recruiter_db_id:
                logger.warning("node.generate_outreach.no_recruiter_id", email=email)
                sent.append(record)
                continue

            try:
                sb.table("outreach").insert({
                    "recruiter_id": recruiter_db_id,
                    "job_id": job_db_id,
                    "channel": "email",
                    "subject": record.get("subject"),
                    "body": record.get("body", ""),
                    "status": "sent" if record.get("sent") else "queued",
                }).execute()
            except Exception as exc:
                logger.error("node.generate_outreach.insert_error", error=str(exc))

            sent.append(record)

    except Exception as exc:
        logger.error("node.generate_outreach.error", error=str(exc))
        state.setdefault("errors", []).append(f"outreach: {exc}")

    state["outreach_sent"] = sent
    logger.info("node.generate_outreach.done",
                sent=len([r for r in sent if r.get("sent")]))
    return state


# ─── Step 6: write daily analytics row ───────────────────────────────────────

async def summarize_node(state: PipelineState) -> PipelineState:
    logger.info("node.summarize.start")
    today = date.today().isoformat()

    scored = state.get("scored_jobs", [])
    analytics_row = {
        "jobs_discovered": len(state.get("raw_jobs", [])),
        "jobs_scored": len([j for j in scored
                            if j.get("composite_score", 0.0) >= _SCORE_THRESHOLD]),
        "applications_submitted": len(state.get("submitted_applications", [])),
        "applications_failed": len(state.get("failed_applications", [])),
        "recruiters_contacted": len([r for r in state.get("outreach_sent", [])
                                     if r.get("sent")]),
        "recruiter_replies": 0,
        "interviews_scheduled": 0,
    }

    def _write_analytics():
        sb = _get_sb()
        existing = sb.table("analytics").select("id").eq("date", today).execute()
        if existing.data:
            sb.table("analytics").update(analytics_row).eq("date", today).execute()
        else:
            sb.table("analytics").insert({"date": today, **analytics_row}).execute()

    try:
        await _run_in_thread(_write_analytics)
        logger.info("node.summarize.analytics_saved", **analytics_row)
    except Exception as exc:
        logger.error("node.summarize.analytics_error", error=str(exc))
        state.setdefault("errors", []).append(f"summarize: {exc}")

    state["daily_stats"] = {
        "jobs_found": len(scored),
        "pending_approvals": len(state.get("pending_approvals", [])),
        "applications_sent": analytics_row["applications_submitted"],
        "recruiters_contacted": analytics_row["recruiters_contacted"],
        "errors": len(state.get("errors", [])),
    }
    state["current_step"] = "complete"
    logger.info("node.summarize.done", **state["daily_stats"])
    return state


# ─── backward-compat aliases (graph.py imports these names) ──────────────────
node_scout_jobs = discover_jobs_node
node_filter_jobs = score_jobs_node
node_tailor_resumes = tailor_resume_node
node_send_outreach = generate_outreach_node
