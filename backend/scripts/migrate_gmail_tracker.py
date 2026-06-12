"""
Migrate Gmail tracker PostgreSQL data → Supabase inbox_emails + email_threads.
Run once: python3 scripts/migrate_gmail_tracker.py

Requires the Gmail tracker Postgres container to be reachable and
GMAIL_TRACKER_PG_* env vars set in backend/.env.

NOTE: This script assumes inbox_emails has been extended with the new columns
added in the gmail-tracker integration migration (gmail_message_id, sender_email,
sender_name, body_preview, full_body, company_name, role_title, pipeline_stage).
Those column renames/additions must be applied in Supabase before running this.
"""
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import psycopg2
from core.supabase_client import get_supabase_client

PG_HOST = os.getenv("GMAIL_TRACKER_PG_HOST", "localhost")
PG_PORT = os.getenv("GMAIL_TRACKER_PG_PORT", "5432")
PG_DB   = os.getenv("GMAIL_TRACKER_PG_DB",   "gmail_tracker")
PG_USER = os.getenv("GMAIL_TRACKER_PG_USER", "postgres")
PG_PASS = os.getenv("GMAIL_TRACKER_PG_PASS", "")


def migrate():
    print("Connecting to Gmail tracker PostgreSQL...")
    try:
        conn = psycopg2.connect(
            host=PG_HOST, port=int(PG_PORT), dbname=PG_DB,
            user=PG_USER, password=PG_PASS,
        )
        cur = conn.cursor()
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        print("Make sure the Gmail tracker Docker container is running.")
        return

    sb = get_supabase_client()

    print("Fetching emails from Gmail tracker...")
    cur.execute("""
        SELECT
            id, thread_id, sender, subject, body, snippet,
            classification, pipeline_stage, draft_reply,
            company_name, role_title, received_at, created_at
        FROM emails
        ORDER BY received_at ASC
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    emails = [dict(zip(cols, row)) for row in rows]
    print(f"Found {len(emails)} emails to migrate")

    migrated = 0
    skipped = 0
    for email in emails:
        try:
            existing = sb.table("inbox_emails").select("id").eq(
                "gmail_message_id", str(email["id"])
            ).execute()
            if existing.data:
                skipped += 1
                continue

            raw_sender = email.get("sender") or ""
            sender_name = raw_sender.split("<")[0].strip().strip('"')

            sb.table("inbox_emails").insert({
                "id":               str(email["id"]),
                "gmail_message_id": str(email["id"]),
                "thread_id":        email.get("thread_id"),
                "sender_email":     raw_sender,
                "sender_name":      sender_name,
                "subject":          email.get("subject"),
                "body_preview":     (email.get("snippet") or "")[:500],
                "full_body":        email.get("body"),
                "classification":   email.get("classification") or "other",
                "pipeline_stage":   email.get("pipeline_stage") or "classified",
                "draft_reply":      email.get("draft_reply"),
                "company_name":     email.get("company_name"),
                "role_title":       email.get("role_title"),
                "received_at":      email["received_at"].isoformat() if email.get("received_at") else None,
                "processed_at":     datetime.now(timezone.utc).isoformat(),
                "reply_sent":       False,
            }).execute()
            migrated += 1

        except Exception as e:
            print(f"Error migrating email {email['id']}: {e}")
            continue

    print(f"Migrated: {migrated}, Skipped (duplicates): {skipped}")

    print("Building email_threads...")
    threads_result = sb.table("inbox_emails").select(
        "thread_id, company_name, role_title, pipeline_stage, "
        "subject, sender_email, received_at, draft_reply"
    ).not_.is_("thread_id", "null").execute()

    threads: dict = {}
    for email in (threads_result.data or []):
        tid = email["thread_id"]
        if tid not in threads:
            threads[tid] = {
                "thread_id":      tid,
                "company_name":   email.get("company_name"),
                "role_title":     email.get("role_title"),
                "pipeline_stage": email.get("pipeline_stage") or "classified",
                "email_count":    0,
                "last_email_at":  None,
                "last_subject":   None,
                "last_sender":    None,
                "has_draft_reply": False,
            }
        threads[tid]["email_count"] += 1
        if email.get("draft_reply"):
            threads[tid]["has_draft_reply"] = True
        recv = email.get("received_at")
        if recv and (not threads[tid]["last_email_at"] or recv > threads[tid]["last_email_at"]):
            threads[tid]["last_email_at"] = recv
            threads[tid]["last_subject"]  = email.get("subject")
            threads[tid]["last_sender"]   = email.get("sender_email")

    thread_count = 0
    for thread in threads.values():
        try:
            sb.table("email_threads").upsert(thread, on_conflict="thread_id").execute()
            thread_count += 1
        except Exception as e:
            print(f"Error inserting thread {thread['thread_id']}: {e}")

    print(f"Created/updated {thread_count} email threads")
    print("Migration complete!")
    cur.close()
    conn.close()


if __name__ == "__main__":
    migrate()
