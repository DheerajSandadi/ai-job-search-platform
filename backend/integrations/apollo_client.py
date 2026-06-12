from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from core.config import settings

logger = structlog.get_logger()

BASE_URL = "https://api.apollo.io/api/v1"

RECRUITER_TITLES = [
    "Technical Recruiter",
    "Engineering Recruiter",
    "Software Engineering Recruiter",
    "Talent Acquisition",
    "Head of Recruiting",
    "Director of Talent",
]


class ApolloClient:
    """Apollo.io people search for recruiter discovery."""

    _PLACEHOLDERS = {"", "your-apollo-key", "your_apollo_key", "changeme"}

    def __init__(self) -> None:
        key = settings.APOLLO_API_KEY
        if not key or key in self._PLACEHOLDERS:
            logger.warning("apollo_not_configured", msg="APOLLO_API_KEY not set — recruiter search disabled")
            self._key = None
        else:
            self._key = key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search_recruiters(
        self,
        company: str,
        titles: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        if not self._key:
            logger.warning("apollo_disabled")
            return []

        titles = titles or RECRUITER_TITLES
        logger.info("apollo_search_recruiters", company=company)

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{BASE_URL}/mixed_people/search",
                    headers={
                        "Content-Type": "application/json",
                        "Cache-Control": "no-cache",
                        "X-Api-Key": self._key,
                    },
                    json={
                        "page": 1,
                        "per_page": limit,
                        "person_titles": titles,
                        "organization_names": [company],
                        "contact_email_status": ["verified", "guessed", "unavailable", "bounced", "pending_manual_fulfillment"],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                people = data.get("people", [])
                logger.info("apollo_results", company=company, count=len(people))
                return people
        except httpx.HTTPStatusError as exc:
            logger.error("apollo_http_error", status=exc.response.status_code, company=company)
            return []
        except httpx.RequestError as exc:
            logger.error("apollo_request_error", error=str(exc), company=company)
            return []

    def normalize(self, raw: dict) -> dict:
        org = raw.get("organization") or {}
        email = raw.get("email") or (
            (raw.get("contact") or {}).get("email")
        )
        return {
            "name": raw.get("name") or f"{raw.get('first_name', '')} {raw.get('last_name', '')}".strip(),
            "email": email,
            "linkedin_url": raw.get("linkedin_url"),
            "company": org.get("name") or raw.get("organization_name", ""),
            "title": raw.get("title", ""),
            "source": "apollo",
        }


def get_apollo_client() -> ApolloClient:
    return ApolloClient()
