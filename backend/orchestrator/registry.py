"""Maps application ids to LangGraph thread ids so the approve/reject/
mark-applied API routes can find and resume the paused graph run that created
a given application.

Kept in a small local sqlite file (separate from the LangGraph checkpoint db to
avoid lock contention with aiosqlite) because the Supabase schema is frozen for
this phase — no new columns allowed.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import structlog

from core.config import settings

logger = structlog.get_logger()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS approval_threads (
    application_id TEXT PRIMARY KEY,
    thread_id      TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def _connect() -> sqlite3.Connection:
    path = Path(settings.ORCHESTRATOR_REGISTRY_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.execute(_SCHEMA)
    return conn


def register_application_thread(application_id: str, thread_id: str) -> None:
    """Record which graph thread produced an application (select-then-write)."""
    with _connect() as conn:
        existing = conn.execute(
            "SELECT thread_id FROM approval_threads WHERE application_id = ?",
            (application_id,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE approval_threads SET thread_id = ? WHERE application_id = ?",
                (thread_id, application_id),
            )
        else:
            conn.execute(
                "INSERT INTO approval_threads (application_id, thread_id) VALUES (?, ?)",
                (application_id, thread_id),
            )


def lookup_thread(application_id: str) -> str | None:
    """Return the graph thread id for an application, or None if unknown
    (e.g. rows created before the orchestrator existed)."""
    try:
        if not Path(settings.ORCHESTRATOR_REGISTRY_DB).exists():
            return None  # no run has registered anything yet — don't create the db on reads
        with _connect() as conn:
            row = conn.execute(
                "SELECT thread_id FROM approval_threads WHERE application_id = ?",
                (application_id,),
            ).fetchone()
        return row[0] if row else None
    except sqlite3.Error as exc:
        logger.error("registry.lookup_failed", application_id=application_id, error=str(exc))
        return None
