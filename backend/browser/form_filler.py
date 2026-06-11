from __future__ import annotations

import asyncio
import structlog
from playwright.async_api import Page
from browser.selectors import detect_ats
from browser.playwright_runner import new_page, navigate, close_context

logger = structlog.get_logger()

APPLICANT = {
    "first_name": "Dheeraj",
    "last_name": "Reddy",
    "email": "dheerajreddysandadi@icloud.com",
    "phone": "",
}


async def fill_application(
    job_url: str,
    resume_path: str,
    cover_letter: str | None = None,
) -> dict:
    """
    Navigate to job URL, detect ATS, fill and submit the application form.
    Returns {"success": bool, "error": str | None}.
    """
    context, page = await new_page()
    result: dict = {"success": False, "error": None}

    try:
        selectors = detect_ats(job_url)
        await navigate(page, job_url)

        # Click "Apply" button if the ATS requires it
        apply_btn = selectors.get("apply_btn")
        if apply_btn:
            try:
                await page.click(apply_btn, timeout=5_000)
                await page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception:
                pass

        # Fill text fields
        for field, selector in selectors.items():
            if field in ("apply_btn", "resume_upload", "cover_letter", "submit", "next_btn"):
                continue
            value = APPLICANT.get(field, "")
            if not value:
                continue
            try:
                await page.fill(selector, value, timeout=3_000)
            except Exception:
                pass

        # Upload resume
        resume_sel = selectors.get("resume_upload")
        if resume_sel and resume_path:
            try:
                await page.set_input_files(resume_sel, resume_path, timeout=5_000)
                await asyncio.sleep(1)
            except Exception as exc:
                logger.warning("resume_upload_failed", error=str(exc))

        # Fill cover letter
        cl_sel = selectors.get("cover_letter")
        if cl_sel and cover_letter:
            try:
                await page.fill(cl_sel, cover_letter, timeout=3_000)
            except Exception:
                pass

        # Submit
        submit_sel = selectors.get("submit", "button[type='submit']")
        await page.click(submit_sel, timeout=5_000)
        await page.wait_for_load_state("networkidle", timeout=15_000)

        result["success"] = True
        logger.info("application_submitted", url=job_url)

    except Exception as exc:
        result["error"] = str(exc)
        logger.error("application_failed", url=job_url, error=str(exc))
    finally:
        await close_context(context)

    return result
