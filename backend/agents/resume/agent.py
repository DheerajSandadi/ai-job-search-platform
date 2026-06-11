from __future__ import annotations

import structlog
from agents.resume.tools import tailor_resume, load_base_resume

logger = structlog.get_logger()


def run(jobs: list[dict]) -> list[dict]:
    """
    Tailor resumes for each approved job.
    Returns list of dicts: {"job": {...}, "resume": {tailored resume data}}.
    """
    base_resume = load_base_resume()
    logger.info("resume_agent_started", job_count=len(jobs))
    results: list[dict] = []

    for job in jobs:
        logger.info("tailoring_resume", title=job.get("title"), company=job.get("company"))
        resume_data = tailor_resume(job, base_resume)
        results.append({"job": job, "resume": resume_data})

    logger.info("resume_agent_complete", tailored=len(results))
    return results
