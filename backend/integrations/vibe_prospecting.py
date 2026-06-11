from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from core.config import settings

logger = structlog.get_logger()

BASE_URL = "https://api.vibe.co/v1"


class VibeProspectingClient:
    """HTTP client for the Vibe Prospecting API (recruiter discovery)."""

    def __init__(self) -> None:
        if not settings.VIBE_PROSPECTING_API_KEY:
            logger.warning("vibe_not_configured", msg="VIBE_PROSPECTING_API_KEY missing")
        self._headers = {
            "Authorization": f"Bearer {settings.VIBE_PROSPECTING_API_KEY}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search_recruiters(
        self,
        company: str,
        titles: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        if not settings.VIBE_PROSPECTING_API_KEY:
            logger.warning("vibe_disabled")
            return []

        titles = titles or ["Technical Recruiter", "Engineering Recruiter", "Talent Acquisition", "Head of Recruiting"]
        logger.info("vibe_search_recruiters", company=company, titles=titles)

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{BASE_URL}/people/search",
                    headers=self._headers,
                    json={
                        "company": company,
                        "titles": titles,
                        "limit": limit,
                        "enrich_email": True,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                logger.info("vibe_results", company=company, count=len(results))
                return results
        except httpx.HTTPStatusError as exc:
            logger.error("vibe_http_error", status=exc.response.status_code, company=company)
            return []
        except httpx.RequestError as exc:
            logger.error("vibe_request_error", error=str(exc), company=company)
            return []

    def normalize(self, raw: dict) -> dict:
        return {
            "name": raw.get("full_name", raw.get("name", "")),
            "email": raw.get("email"),
            "linkedin_url": raw.get("linkedin_url"),
            "company": raw.get("company", raw.get("organization", "")),
            "title": raw.get("title", ""),
            "source": "vibe",
        }


def get_vibe_client() -> VibeProspectingClient:
    return VibeProspectingClient()
