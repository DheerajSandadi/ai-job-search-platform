from __future__ import annotations

import structlog
from agents.recruiter.tools import find_recruiters, rank_recruiters

logger = structlog.get_logger()


def run(jobs: list[dict]) -> list[dict]:
    """
    Find and rank recruiters for each job's company.
    Returns list of {"job": {...}, "recruiters": [...]}.
    Deduplicates by company so we don't search the same company twice.
    """
    logger.info("recruiter_agent_started", job_count=len(jobs))
    seen_companies: set[str] = set()
    results: list[dict] = []

    for job in jobs:
        company = job.get("company", "")
        if not company or company in seen_companies:
            continue
        seen_companies.add(company)

        raw = find_recruiters(company, job.get("title", ""))
        ranked = rank_recruiters(company, job.get("title", ""), raw)
        if ranked:
            results.append({"job": job, "recruiters": ranked})
            logger.info("recruiters_found", company=company, count=len(ranked))

    logger.info("recruiter_agent_complete", companies_searched=len(seen_companies), results=len(results))
    return results
