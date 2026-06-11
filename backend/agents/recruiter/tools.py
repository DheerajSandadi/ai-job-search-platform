from __future__ import annotations

import json
import structlog
from core.anthropic_client import anthropic_client, HAIKU
from agents.recruiter.prompts import FIND_SYSTEM, FIND_USER
from integrations.vibe_prospecting import get_vibe_client

logger = structlog.get_logger()


def find_recruiters(company: str, role: str, limit: int = 10) -> list[dict]:
    """Find recruiters at a company via Vibe Prospecting."""
    client = get_vibe_client()
    raw = client.search_recruiters(company, limit=limit)
    if not raw:
        logger.warning("no_recruiters_found", company=company)
        return []
    return [client.normalize(r) for r in raw]


def rank_recruiters(company: str, role: str, recruiters: list[dict]) -> list[dict]:
    """Use Claude Haiku to rank and select the best recruiters to contact."""
    if not recruiters:
        return []
    try:
        profiles_str = "\n".join(
            f"{i}. {r.get('name')} — {r.get('title')} (email: {r.get('email') or 'unknown'})"
            for i, r in enumerate(recruiters)
        )
        raw = anthropic_client.call_claude(
            model=HAIKU,
            system=FIND_SYSTEM,
            user=FIND_USER.format(company=company, role=role, profiles=profiles_str),
            max_tokens=256,
        )
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        selected_indices = result.get("selected", [])
        selected = [recruiters[i] for i in selected_indices if i < len(recruiters)]
        logger.info("recruiters_ranked", company=company, selected=len(selected))
        return selected
    except Exception as exc:
        logger.error("recruiter_rank_failed", error=str(exc))
        return recruiters[:3]
