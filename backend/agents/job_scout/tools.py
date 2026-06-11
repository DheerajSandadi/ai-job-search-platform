from __future__ import annotations

import json
import structlog
from core.anthropic_client import anthropic_client, HAIKU
from agents.job_scout.prompts import SCORE_SYSTEM, SCORE_USER
from integrations.apify_client import get_apify_client

logger = structlog.get_logger()


def search_jobs(
    queries: list[str],
    location: str = "Remote",
    max_per_query: int = 15,
) -> list[dict]:
    """Run job searches across Indeed and LinkedIn via Apify."""
    client = get_apify_client()
    all_jobs: list[dict] = []

    if client._client is None:
        logger.warning("search_jobs_skipped", reason="Apify not configured")
        return []

    source_errors: list[str] = []

    for query in queries:
        try:
            raw_indeed = client.search_indeed(query, location, max_per_query)
            all_jobs.extend(client.normalize_indeed(r) for r in raw_indeed)
        except Exception as exc:
            logger.warning("indeed_search_failed", query=query, error=str(exc))
            source_errors.append(f"indeed:{query}:{exc}")

        try:
            raw_linkedin = client.search_linkedin(query, location, max_per_query)
            all_jobs.extend(client.normalize_linkedin(r) for r in raw_linkedin)
        except Exception as exc:
            logger.warning("linkedin_search_failed", query=query, error=str(exc))
            source_errors.append(f"linkedin:{query}:{exc}")

    # Deduplicate by URL
    seen: set[str] = set()
    unique: list[dict] = []
    for job in all_jobs:
        key = job.get("url", "") or f"{job['company']}::{job['title']}"
        if key not in seen:
            seen.add(key)
            unique.append(job)

    logger.info("jobs_discovered", count=len(unique), source_errors=len(source_errors))
    if not unique and source_errors:
        raise RuntimeError(f"All job sources failed: {source_errors[0]}")
    return unique


def score_job(job: dict) -> dict:
    """Use Claude Haiku to score a single job posting. Returns job dict with scores added."""
    try:
        user_msg = SCORE_USER.format(
            title=job.get("title", ""),
            company=job.get("company", ""),
            location=job.get("location", ""),
            description=(job.get("description", "") or "")[:3000],
        )
        raw = anthropic_client.call_claude(
            model=HAIKU,
            system=SCORE_SYSTEM,
            user=user_msg,
            max_tokens=256,
        )
        # Strip markdown code fences if present (Claude sometimes adds them)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        scores = json.loads(raw.strip())
        job["ats_score"] = float(scores.get("ats_score", 0.0))
        job["relevance_score"] = float(scores.get("relevance_score", 0.0))
        job["composite_score"] = float(scores.get("composite_score", 0.0))
        logger.info("job_scored", title=job["title"], company=job["company"], composite=job["composite_score"])
    except Exception as exc:
        logger.error("job_score_failed", title=job.get("title"), error=str(exc))
        job.setdefault("ats_score", 0.0)
        job.setdefault("relevance_score", 0.0)
        job.setdefault("composite_score", 0.0)
    return job


def filter_jobs(jobs: list[dict], min_score: float = 0.6) -> list[dict]:
    return [j for j in jobs if j.get("composite_score", 0.0) >= min_score]
