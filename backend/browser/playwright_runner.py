from __future__ import annotations

import asyncio
import structlog
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logger = structlog.get_logger()

_browser: Browser | None = None
_context: BrowserContext | None = None


async def get_browser() -> Browser:
    global _browser
    if _browser is None or not _browser.is_connected():
        pw = await async_playwright().start()
        _browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        logger.info("browser_launched")
    return _browser


async def new_page() -> tuple[BrowserContext, Page]:
    browser = await get_browser()
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )
    page = await context.new_page()
    return context, page


async def navigate(page: Page, url: str, wait_until: str = "networkidle") -> None:
    logger.info("browser_navigate", url=url)
    await page.goto(url, wait_until=wait_until, timeout=30_000)


async def close_context(context: BrowserContext) -> None:
    try:
        await context.close()
    except Exception:
        pass


async def shutdown_browser() -> None:
    global _browser
    if _browser:
        await _browser.close()
        _browser = None
        logger.info("browser_shutdown")
