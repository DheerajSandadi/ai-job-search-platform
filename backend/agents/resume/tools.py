from __future__ import annotations

import json
import structlog
from core.anthropic_client import anthropic_client, SONNET, HAIKU
from agents.resume.prompts import TAILOR_SYSTEM, TAILOR_USER, SCORE_SYSTEM, SCORE_USER

logger = structlog.get_logger()

BASE_RESUME_PATH = "./resume.txt"


def load_base_resume() -> str:
    try:
        with open(BASE_RESUME_PATH) as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("base_resume_not_found", path=BASE_RESUME_PATH)
        return (
            "Dheeraj Reddy\n"
            "dheerajreddysandadi@icloud.com\n\n"
            "EXPERIENCE\n"
            "Software Engineer — 5+ years building ML systems, APIs, and data pipelines.\n"
            "Skills: Python, FastAPI, LangChain, PyTorch, React, Next.js, PostgreSQL, GCP.\n"
        )


def tailor_resume(job: dict, base_resume: str | None = None) -> dict:
    if base_resume is None:
        base_resume = load_base_resume()

    description = (job.get("description") or "")[:4000]
    try:
        user_msg = TAILOR_USER.format(
            title=job.get("title", ""),
            company=job.get("company", ""),
            description=description,
            resume_text=base_resume[:4000],
        )
        raw = anthropic_client.call_claude(
            model=SONNET,
            system=TAILOR_SYSTEM,
            user=user_msg,
            max_tokens=8192,
        )
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        logger.info("resume_tailored", title=job.get("title"), company=job.get("company"))
        return {
            "original_text": base_resume,
            "tailored_text": result.get("tailored_text", base_resume),
            "diff_summary": result.get("diff_summary", ""),
            "ats_score": float(result.get("ats_score", 0.0)),
            "keywords_added": result.get("keywords_added", []),
        }
    except Exception as exc:
        logger.error("resume_tailor_failed", error=str(exc))
        return {
            "original_text": base_resume,
            "tailored_text": base_resume,
            "diff_summary": "Tailoring failed; using original resume.",
            "ats_score": 0.0,
            "keywords_added": [],
        }


def score_resume(job: dict, resume_text: str) -> float:
    try:
        raw = anthropic_client.call_claude(
            model=HAIKU,
            system=SCORE_SYSTEM,
            user=SCORE_USER.format(
                description=(job.get("description") or "")[:2000],
                resume_text=resume_text[:2000],
            ),
            max_tokens=128,
        )
        return float(json.loads(raw).get("ats_score", 0.0))
    except Exception:
        return 0.0
