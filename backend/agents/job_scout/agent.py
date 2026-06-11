from __future__ import annotations

import structlog
from agents.job_scout.tools import search_jobs, score_job, filter_jobs

logger = structlog.get_logger()

DEFAULT_QUERIES = [
    "AI Engineer Python",
    "ML Engineer LLM",
    "Staff Software Engineer AI",
    "Senior Machine Learning Engineer",
    "AI Research Engineer",
]


def run(
    queries: list[str] | None = None,
    location: str = "Remote",
    min_score: float = 0.65,
    max_per_query: int = 15,
) -> list[dict]:
    """
    Discover, score, and filter jobs.
    Returns a list of job dicts with ats_score, relevance_score, composite_score.
    """
    queries = queries or DEFAULT_QUERIES
    logger.info("job_scout_started", queries=queries, location=location)

    raw_jobs = search_jobs(queries, location, max_per_query)
    if not raw_jobs:
        logger.warning("job_scout_no_results")
        return []

    scored = [score_job(job) for job in raw_jobs]
    filtered = filter_jobs(scored, min_score)

    logger.info("job_scout_complete", total=len(raw_jobs), scored=len(scored), filtered=len(filtered))
    return filtered
