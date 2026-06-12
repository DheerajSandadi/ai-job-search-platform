"""
Backfill company_name and role_title for email_threads from inbox_emails.
Run once: python3 scripts/backfill_threads.py
"""
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from core.supabase_client import get_supabase_client

sb = get_supabase_client()

threads = sb.table("email_threads").select(
    "id, thread_id, company_name, role_title"
).is_("company_name", "null").execute()

print(f"Threads to backfill: {len(threads.data)}")

updated = 0
for thread in threads.data:
    email = sb.table("inbox_emails").select(
        "company_name, role_title, sender_name, subject"
    ).eq("thread_id", thread["thread_id"]).not_.is_(
        "company_name", "null"
    ).order("received_at", desc=True).limit(1).execute()

    if email.data:
        sb.table("email_threads").update({
            "company_name": email.data[0].get("company_name"),
            "role_title":   email.data[0].get("role_title"),
        }).eq("id", thread["id"]).execute()
        updated += 1

print(f"Updated: {updated} threads")
print("Done!")
