from __future__ import annotations

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from apify_client import ApifyClient as _ApifyClient
from core.config import settings

logger = structlog.get_logger()


class ApifyJobClient:
    """Thin wrapper around the Apify client for job-board scraping."""

    ACTOR_INDEED = "misceres/indeed-scraper"
    ACTOR_LINKEDIN = "curious_coder/linkedin-jobs-scraper"

    _PLACEHOLDERS = {"", "your-apify-key", "your_apify_key", "changeme"}

    def __init__(self) -> None:
        key = settings.APIFY_API_KEY
        if not key or key in self._PLACEHOLDERS:
            logger.warning("apify_not_configured", msg="APIFY_API_KEY not set — job search disabled")
            self._client = None
        else:
            self._client = _ApifyClient(key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search_indeed(
        self,
        query: str,
        location: str = "Remote",
        max_results: int = 25,
    ) -> list[dict]:
        if not self._client:
            logger.warning("apify_disabled", source="indeed")
            return []
        logger.info("apify_search_indeed", query=query, location=location)
        run = self._client.actor(self.ACTOR_INDEED).call(
            run_input={
                "position": query,
                "location": location,
                "maxItems": max_results,
                "country": "US",
            }
        )
        items = list(self._client.dataset(run["defaultDatasetId"]).iterate_items())
        logger.info("apify_indeed_results", count=len(items))
        return items

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search_linkedin(
        self,
        query: str,
        location: str = "United States",
        max_results: int = 25,
    ) -> list[dict]:
        if not self._client:
            logger.warning("apify_disabled", source="linkedin")
            return []
        logger.info("apify_search_linkedin", query=query, location=location)
        run = self._client.actor(self.ACTOR_LINKEDIN).call(
            run_input={
                "keywords": query,
                "location": location,
                "maxItems": max_results,
            }
        )
        items = list(self._client.dataset(run["defaultDatasetId"]).iterate_items())
        logger.info("apify_linkedin_results", count=len(items))
        return items

    def normalize_indeed(self, raw: dict) -> dict:
        return {
            "title": raw.get("positionName", ""),
            "company": raw.get("company", ""),
            "location": raw.get("location", ""),
            "url": raw.get("url", ""),
            "description": raw.get("description", ""),
            "source": "indeed",
            "raw_data": raw,
        }

    def normalize_linkedin(self, raw: dict) -> dict:
        return {
            "title": raw.get("title", ""),
            "company": raw.get("companyName", ""),
            "location": raw.get("location", ""),
            "url": raw.get("jobUrl", raw.get("url", "")),
            "description": raw.get("description", ""),
            "source": "linkedin",
            "raw_data": raw,
        }


def get_apify_client() -> ApifyJobClient:
    return ApifyJobClient()
