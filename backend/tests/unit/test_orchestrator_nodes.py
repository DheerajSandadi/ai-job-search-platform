"""Unit tests per LangGraph node — agents and Supabase mocked, asserting the
state transitions for success and error paths (spec §8)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.config import settings
from orchestrator.state import initial_state
from tests.conftest import FakeSupabase, make_id


@pytest.fixture(autouse=True)
def _fixed_gate(monkeypatch):
    monkeypatch.setattr(settings, "ATS_CONFIDENCE_THRESHOLD", 0.8)


def _state(**over):
    s = initial_state(make_id(), "2026-07-09T06:00:00+00:00")
    s.update(over)
    return s


def _job(url="https://acme.ai/1", score=0.9):
    return {
        "title": "ML Engineer", "company": "Acme AI", "location": "Remote",
        "url": url, "description": "Build LLM pipelines", "source": "dice",
        "ats_score": score, "relevance_score": score, "composite_score": score,
    }


# ─── discover_jobs ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_discover_jobs_inserts_and_populates_state():
    from orchestrator.nodes import discover_jobs

    sb = FakeSupabase()
    with patch("orchestrator.nodes.search_jobs", return_value=[_job()]), \
         patch("orchestrator.nodes._get_sb", return_value=sb):
        result = await discover_jobs(_state())

    assert len(result["raw_jobs"]) == 1
    assert len(sb.store["jobs"]) == 1
    assert sb.store["jobs"][0]["status"] == "discovered"


@pytest.mark.asyncio
async def test_discover_jobs_drops_non_http_urls():
    from orchestrator.nodes import discover_jobs

    sb = FakeSupabase()
    bad = _job(url="javascript:alert(1)")
    with patch("orchestrator.nodes.search_jobs", return_value=[bad]), \
         patch("orchestrator.nodes._get_sb", return_value=sb):
        result = await discover_jobs(_state())

    assert result["raw_jobs"][0]["url"] == ""
    assert sb.store["jobs"][0]["url"] == ""


@pytest.mark.asyncio
async def test_discover_jobs_captures_error_without_raising():
    from orchestrator.nodes import discover_jobs

    with patch("orchestrator.nodes.search_jobs", side_effect=RuntimeError("Apify down")), \
         patch("orchestrator.nodes._get_sb", return_value=FakeSupabase()):
        result = await discover_jobs(_state())

    assert any("discover_jobs" in e for e in result["errors"])
    assert result["raw_jobs"] == []


# ─── score_jobs ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_score_jobs_populates_approved_jobs_above_gate():
    from orchestrator.nodes import score_jobs

    raw = [_job("https://a/1"), _job("https://a/2")]
    scored = [
        {**raw[0], "composite_score": 0.9},
        {**raw[1], "composite_score": 0.5},
    ]
    with patch("orchestrator.nodes.score_job", side_effect=lambda j: scored[raw.index(j)]), \
         patch("orchestrator.nodes._get_sb", return_value=FakeSupabase()):
        result = await score_jobs(_state(raw_jobs=raw))

    assert len(result["scored_jobs"]) == 2
    assert [j["composite_score"] for j in result["approved_jobs"]] == [0.9]


@pytest.mark.asyncio
async def test_score_jobs_error_leaves_approved_empty():
    from orchestrator.nodes import score_jobs

    with patch("orchestrator.nodes.score_job", side_effect=RuntimeError("llm down")), \
         patch("orchestrator.nodes._get_sb", return_value=FakeSupabase()):
        result = await score_jobs(_state(raw_jobs=[_job()]))

    assert any("score_jobs" in e for e in result["errors"])
    assert result["approved_jobs"] == []


# ─── tailor_resume ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tailor_resume_creates_pending_application_and_registers_thread():
    from orchestrator.nodes import tailor_resume

    sb = FakeSupabase()
    job = _job()
    sb.store["jobs"] = [{"id": make_id(), "url": job["url"], "status": "scored"}]
    resume_payload = {"job": job, "resume": {
        "original_text": "orig", "tailored_text": "tailored",
        "diff_summary": "diff", "ats_score": 0.88, "keywords_added": ["LLM"],
    }}

    with patch("orchestrator.nodes.resume_agent") as agent, \
         patch("orchestrator.persistence.registry") as reg, \
         patch("orchestrator.nodes._get_sb", return_value=sb):
        agent.run.return_value = [resume_payload]
        state = _state(approved_jobs=[job])
        result = await tailor_resume(state)

    assert len(result["pending_approvals"]) == 1
    entry = result["pending_approvals"][0]
    assert entry["application_id"]
    assert sb.store["applications"][0]["status"] == "pending"
    assert sb.store["jobs"][0]["status"] == "pending_approval"
    reg.register_application_thread.assert_called_once_with(
        entry["application_id"], state["run_id"])


@pytest.mark.asyncio
async def test_tailor_resume_agent_failure_is_captured_per_job():
    from orchestrator.nodes import tailor_resume

    with patch("orchestrator.nodes.resume_agent") as agent, \
         patch("orchestrator.nodes._get_sb", return_value=FakeSupabase()):
        agent.run.side_effect = RuntimeError("sonnet down")
        result = await tailor_resume(_state(approved_jobs=[_job()]))

    assert result["pending_approvals"] == []
    assert any("tailor_resume" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_tailor_resume_noop_without_approved_jobs():
    from orchestrator.nodes import tailor_resume

    result = await tailor_resume(_state())
    assert result["pending_approvals"] == []
    assert result["errors"] == []


# ─── await_approval ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_await_approval_is_a_noop_checkpoint():
    from orchestrator.nodes import await_approval

    state = _state(pending_approvals=[{"application_id": "a"}])
    result = await await_approval(state)
    assert result["current_step"] == "await_approval"
    assert result["pending_approvals"] == [{"application_id": "a"}]


# ─── find_recruiters ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_recruiters_targets_submitted_applications():
    from orchestrator.nodes import find_recruiters

    sb = FakeSupabase()
    submitted = [{"title": "ML Engineer", "company": "Acme AI",
                  "application_id": make_id()}]
    batch = {"job": submitted[0],
             "recruiters": [{"name": "R", "email": "r@acme.ai", "title": "TA",
                             "company": "Acme AI"}]}

    with patch("orchestrator.nodes.recruiter_agent") as agent, \
         patch("orchestrator.nodes._get_sb", return_value=sb):
        agent.run.return_value = [batch]
        result = await find_recruiters(_state(submitted_applications=submitted))

    agent.run.assert_called_once_with(submitted)
    assert len(result["recruiters"]) == 1
    assert len(sb.store["recruiters"]) == 1
    assert result["outreach_queue"] == [batch]


@pytest.mark.asyncio
async def test_find_recruiters_noop_without_submissions():
    from orchestrator.nodes import find_recruiters

    with patch("orchestrator.nodes.recruiter_agent") as agent:
        result = await find_recruiters(_state())

    agent.run.assert_not_called()
    assert result["recruiters"] == []


@pytest.mark.asyncio
async def test_find_recruiters_error_is_captured():
    from orchestrator.nodes import find_recruiters

    with patch("orchestrator.nodes.recruiter_agent") as agent, \
         patch("orchestrator.nodes._get_sb", return_value=FakeSupabase()):
        agent.run.side_effect = RuntimeError("apollo 500")
        result = await find_recruiters(
            _state(submitted_applications=[{"company": "Acme"}]))

    assert any("find_recruiters" in e for e in result["errors"])
    assert result["recruiters"] == []


# ─── generate_outreach ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_outreach_drafts_and_queues_rows():
    from orchestrator.nodes import generate_outreach

    sb = FakeSupabase()
    rec = {"name": "R", "email": "r@acme.ai"}
    sb.store["recruiters"] = [{"id": make_id(), "email": "r@acme.ai"}]
    batch = {"job": {"title": "ML", "company": "Acme", "job_id": make_id()},
             "recruiters": [rec]}

    with patch("orchestrator.nodes.outreach_agent") as agent, \
         patch("orchestrator.nodes._get_sb", return_value=sb):
        agent.run.return_value = [{
            "recruiter": rec, "job": batch["job"],
            "subject": "Hi", "body": "Just applied", "sent": False,
        }]
        result = await generate_outreach(_state(outreach_queue=[batch]))

    # drafted only — dry_run must be requested
    assert agent.run.call_args.args[1] is True
    assert len(result["outreach_queue"]) == 1
    drafted = result["outreach_queue"][0]
    assert drafted["outreach_id"]
    assert sb.store["outreach"][0]["status"] == "queued"
    assert drafted["sent"] is False


@pytest.mark.asyncio
async def test_generate_outreach_error_is_captured():
    from orchestrator.nodes import generate_outreach

    with patch("orchestrator.nodes.outreach_agent") as agent, \
         patch("orchestrator.nodes._get_sb", return_value=FakeSupabase()):
        agent.run.side_effect = RuntimeError("draft failed")
        result = await generate_outreach(
            _state(outreach_queue=[{"job": {}, "recruiters": [{}]}]))

    assert any("generate_outreach" in e for e in result["errors"])
    assert result["outreach_queue"] == []


# ─── send_outreach ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_outreach_sends_and_marks_row_sent():
    from orchestrator.nodes import send_outreach

    sb = FakeSupabase()
    oid = make_id()
    sb.store["outreach"] = [{"id": oid, "status": "queued"}]
    record = {"recruiter": {"email": "r@acme.ai"}, "job": {},
              "subject": "Hi", "body": "b", "outreach_id": oid, "sent": False}

    with patch("orchestrator.nodes.send_email", return_value=True) as send, \
         patch("orchestrator.nodes._get_sb", return_value=sb):
        result = await send_outreach(_state(outreach_queue=[record]))

    send.assert_called_once_with("r@acme.ai", "Hi", "b")
    assert result["outreach_sent"][0]["sent"] is True
    assert sb.store["outreach"][0]["status"] == "sent"


@pytest.mark.asyncio
async def test_send_outreach_failure_keeps_row_queued():
    from orchestrator.nodes import send_outreach

    sb = FakeSupabase()
    oid = make_id()
    sb.store["outreach"] = [{"id": oid, "status": "queued"}]
    record = {"recruiter": {"email": "r@acme.ai"}, "job": {},
              "subject": "Hi", "body": "b", "outreach_id": oid, "sent": False}

    with patch("orchestrator.nodes.send_email", side_effect=RuntimeError("smtp")), \
         patch("orchestrator.nodes._get_sb", return_value=sb):
        result = await send_outreach(_state(outreach_queue=[record]))

    assert result["outreach_sent"][0]["sent"] is False
    assert sb.store["outreach"][0]["status"] == "queued"
    assert any("send_outreach" in e for e in result["errors"])


# ─── log_skip / log_rejection ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_skip_is_informational():
    from orchestrator.nodes import log_skip

    result = await log_skip(_state(scored_jobs=[{"composite_score": 0.3}]))
    assert result["current_step"] == "log_skip"
    assert any("log_skip" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_log_rejection_is_informational():
    from orchestrator.nodes import log_rejection

    result = await log_rejection(_state())
    assert result["current_step"] == "log_rejection"
    assert any("log_rejection" in e for e in result["errors"])


# ─── update_analytics ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_analytics_inserts_daily_row():
    from orchestrator.nodes import update_analytics

    sb = FakeSupabase()
    state = _state(
        raw_jobs=[{}] * 5,
        scored_jobs=[{"composite_score": 0.9}] * 3 + [{"composite_score": 0.2}],
        outreach_sent=[{"sent": True}, {"sent": False}],
    )
    with patch("orchestrator.nodes._get_sb", return_value=sb):
        result = await update_analytics(state)

    assert result["current_step"] == "complete"
    row = sb.store["analytics"][0]
    assert row["jobs_discovered"] == 5
    assert row["jobs_scored"] == 3
    assert row["recruiters_contacted"] == 1


@pytest.mark.asyncio
async def test_update_analytics_followon_run_does_not_clobber_morning_counts():
    from orchestrator.nodes import update_analytics

    sb = FakeSupabase()
    from datetime import date
    sb.store["analytics"] = [{
        "id": make_id(), "date": date.today().isoformat(),
        "jobs_discovered": 30, "jobs_scored": 7,
        "applications_submitted": 2, "recruiters_contacted": 1,
    }]
    # Follow-on outreach run: no raw_jobs, one email sent
    state = _state(outreach_sent=[{"sent": True}])
    with patch("orchestrator.nodes._get_sb", return_value=sb):
        await update_analytics(state)

    row = sb.store["analytics"][0]
    assert row["jobs_discovered"] == 30  # untouched
    assert row["jobs_scored"] == 7       # untouched
    assert row["recruiters_contacted"] == 2  # incremented
    assert row["applications_submitted"] == 2  # owned by mark-applied route
