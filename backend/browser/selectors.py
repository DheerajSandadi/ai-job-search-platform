"""CSS / XPath selectors for common ATS systems."""
from __future__ import annotations

GREENHOUSE = {
    "first_name": "#first_name",
    "last_name": "#last_name",
    "email": "#email",
    "phone": "#phone",
    "resume_upload": "input[type='file']",
    "cover_letter": "#cover_letter",
    "submit": "input[type='submit'], button[type='submit']",
}

LEVER = {
    "name": "input[name='name']",
    "email": "input[name='email']",
    "phone": "input[name='phone']",
    "resume_upload": "input[type='file']",
    "cover_letter": "textarea[name='comments']",
    "submit": ".btn-primary[type='submit'], button[type='submit']",
}

WORKDAY = {
    "apply_btn": "a[data-automation-id='applyButton'], button[data-automation-id='applyButton']",
    "first_name": "input[data-automation-id='firstName']",
    "last_name": "input[data-automation-id='lastName']",
    "email": "input[data-automation-id='email']",
    "phone": "input[data-automation-id='phone']",
    "resume_upload": "input[type='file']",
    "next_btn": "button[data-automation-id='bottom-navigation-next-button']",
    "submit": "button[data-automation-id='bottom-navigation-next-button']",
}

ICIMS = {
    "first_name": "input[name*='firstname'], input[id*='firstName']",
    "last_name": "input[name*='lastname'], input[id*='lastName']",
    "email": "input[name*='email'], input[type='email']",
    "resume_upload": "input[type='file']",
    "submit": "input[type='submit'], button[type='submit']",
}

GENERIC = {
    "first_name": "input[name*='first'], input[id*='first'], input[placeholder*='First']",
    "last_name": "input[name*='last'], input[id*='last'], input[placeholder*='Last']",
    "email": "input[type='email'], input[name*='email']",
    "phone": "input[type='tel'], input[name*='phone']",
    "resume_upload": "input[type='file'][accept*='pdf'], input[type='file']",
    "cover_letter": "textarea[name*='cover'], textarea[placeholder*='cover'], textarea[name*='message']",
    "submit": "button[type='submit'], input[type='submit']",
}


def detect_ats(url: str) -> dict[str, str]:
    u = url.lower()
    if "greenhouse.io" in u or "boards.greenhouse" in u:
        return GREENHOUSE
    if "jobs.lever.co" in u:
        return LEVER
    if "myworkdayjobs.com" in u or "wd" in u:
        return WORKDAY
    if "icims.com" in u:
        return ICIMS
    return GENERIC
