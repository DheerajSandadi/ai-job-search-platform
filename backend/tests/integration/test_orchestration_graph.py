"""End-to-end graph tests against the real compiled StateGraph (MemorySaver),
with agents and Supabase mocked.

Covers the highest-risk behavior per the orchestration spec §8:
- the run interrupts after await_approval (no polling, no blocking),
- approve alone records the decision but keeps the run paused,
- mark-applied resumes into find_recruiters → outreach → analytics,
- reject-all resumes into log_rejection,
- a decision-less resume parks the run at the interrupt again,
- mark-applied on an already-finished run seeds a follow-on thread.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from core.config import settings
from orchestrator.graph import build_graph
from orchestrator.state import initial_state
from tests.conftest import FakeSupabase, make_id

WAIT = ("await_approval",)


def _job(i: int, score: float = 0.9) -> dict:
    return {
        "title": f"ML Engineer {i}", "company": f"Acme {i}", "location": "Remote",
        "url": f"https://acme{i}.ai/jobs/1", "description": "LLM pipelines",
        "source": "dice", "ats_score": score, "relevance_score": score,
        "composite_score": score,
    }


def _resume_stub(jobs: list[dict]) -> list[dict]:
    return [{"job": jobs[0], "resume": {
        "original_text": "orig", "tailored_text": "tailored",
        "diff_summary": "diff", "ats_score": 0.9, "keywords_added": ["LLM"],
    }}]


def _recruiter_stub(jobs: list[dict]) -> list[dict]:
    return [
        {"job": j, "recruiters": [{
            "name": f"Recruiter {n}", "email": f"recruiter{n}@{j['company'].replace(' ', '').lower()}.ai",
            "title": "Technical Recruiter", "company": j["company"],
        }]}
        for n, j in enumerate(jobs)
    ]


def _outreach_stub(batches: list[dict], dry_run: bool = False) -> list[dict]:
    assert dry_run, "generate_outreach must draft with dry_run=True"
    return [
        {"recruiter": r, "job": b["job"], "subject": "Quick intro",
         "body": "I just applied", "sent": False, "dry_run": dry_run}
        for b in batches for r in b["recruiters"]
    ]


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """Real graph + real registry (tmp sqlite) + fake supabase + stub agents."""
    monkeypatch.setattr(settings, "ATS_CONFIDENCE_THRESHOLD", 0.8)
    monkeypatch.setattr(settings, "ORCHESTRATOR_REGISTRY_DB",
                        str(tmp_path / "registry.sqlite"))
    sb = FakeSupabase()
    graph = build_graph(MemorySaver())

    patches = [
        patch("orchestrator.nodes._get_sb", return_value=sb),
        patch("orchestrator.nodes.search_jobs", return_value=[_job(1), _job(2)]),
        patch("orchestrator.nodes.score_job", side_effect=lambda j: j),
        patch("orchestrator.nodes.resume_agent.run", side_effect=_resume_stub),
        patch("orchestrator.nodes.recruiter_agent.run", side_effect=_recruiter_stub),
        patch("orchestrator.nodes.outreach_agent.run", side_effect=_outreach_stub),
        patch("orchestrator.nodes.send_email", return_value=True),
        patch("orchestrator.approvals.get_graph", return_value=graph),
    ]
    for p in patches:
        p.start()
    yield graph, sb
    for p in patches:
        p.stop()


async def _start_run(graph) -> tuple[str, dict, list[dict]]:
    thread_id = make_id()
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.ainvoke(
        initial_state(thread_id, "2026-07-09T06:00:00+00:00"), config=config)
    return thread_id, config, state.get("pending_approvals", [])


# ─── interrupt behavior ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_interrupts_after_await_approval(env):
    graph, sb = env
    _, config, pending = await _start_run(graph)

    snapshot = await graph.aget_state(config)
    assert snapshot.next == WAIT
    assert len(pending) == 2
    assert all(e.get("application_id") for e in pending)
    assert all(a["status"] == "pending" for a in sb.store["applications"])
    # no outreach happened while paused
    assert "outreach" not in sb.store


@pytest.mark.asyncio
async def test_resume_without_decision_keeps_waiting(env):
    graph, _ = env
    _, config, _ = await _start_run(graph)

    await graph.ainvoke(None, config=config)  # nobody decided anything
    snapshot = await graph.aget_state(config)
    assert snapshot.next == WAIT


@pytest.mark.asyncio
async def test_empty_run_skips_checkpoint_and_completes(env):
    graph, sb = env
    with patch("orchestrator.nodes.search_jobs", return_value=[]):
        thread_id = make_id()
        config = {"configurable": {"thread_id": thread_id}}
        state = await graph.ainvoke(
            initial_state(thread_id, "2026-07-09T06:00:00+00:00"), config=config)

    snapshot = await graph.aget_state(config)
    assert snapshot.next == ()  # ran log_skip -> update_analytics -> END
    assert state["current_step"] == "complete"
    assert any("log_skip" in e for e in state["errors"])


# ─── pending → approved → applied cycle ───────────────────────────────────────

@pytest.mark.asyncio
async def test_full_approve_apply_cycle_drives_outreach(env):
    from orchestrator.approvals import apply_human_decision

    graph, sb = env
    _, config, pending = await _start_run(graph)
    app_id = pending[0]["application_id"]

    # 1. Approve: decision recorded, run still paused
    await apply_human_decision(app_id, "approved")
    snapshot = await graph.aget_state(config)
    assert snapshot.next == WAIT
    entry = next(e for e in snapshot.values["pending_approvals"]
                 if e["application_id"] == app_id)
    assert entry["decision"] == "approved"

    # 2. Mark applied: run resumes through outreach to completion
    await apply_human_decision(app_id, "applied")
    snapshot = await graph.aget_state(config)
    assert snapshot.next == ()
    values = snapshot.values
    assert [e["application_id"] for e in values["submitted_applications"]] == [app_id]
    assert values["current_step"] == "complete"
    assert all(r["sent"] for r in values["outreach_sent"])

    # persisted side effects
    assert sb.store["outreach"][0]["status"] == "sent"
    assert len(sb.store["recruiters"]) == 1
    assert sb.store["analytics"], "analytics row written"

    # the second application is still pending in state (handled via follow-on)
    assert len(values["pending_approvals"]) == 1


# ─── pending → rejected path ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reject_all_completes_via_log_rejection(env):
    from orchestrator.approvals import apply_human_decision

    graph, sb = env
    _, config, pending = await _start_run(graph)

    for entry in pending:
        await apply_human_decision(entry["application_id"], "rejected")

    snapshot = await graph.aget_state(config)
    assert snapshot.next == ()
    values = snapshot.values
    assert values["pending_approvals"] == []
    assert values["submitted_applications"] == []
    assert any("log_rejection" in e for e in values["errors"])
    assert "outreach" not in sb.store  # no emails for rejected apps


@pytest.mark.asyncio
async def test_partial_reject_keeps_run_waiting(env):
    from orchestrator.approvals import apply_human_decision

    graph, _ = env
    _, config, pending = await _start_run(graph)

    await apply_human_decision(pending[0]["application_id"], "rejected")
    snapshot = await graph.aget_state(config)
    assert snapshot.next == WAIT
    assert len(snapshot.values["pending_approvals"]) == 1


# ─── follow-on run after the original finished ────────────────────────────────

@pytest.mark.asyncio
async def test_mark_applied_after_run_finished_seeds_followon(env):
    from orchestrator.approvals import apply_human_decision

    graph, sb = env
    thread_id, config, pending = await _start_run(graph)
    first, second = pending[0]["application_id"], pending[1]["application_id"]

    # First application drives the run to completion…
    await apply_human_decision(first, "applied")
    assert (await graph.aget_state(config)).next == ()

    # …then the human applies to the second one hours later.
    await apply_human_decision(second, "applied")

    followup = {"configurable": {
        "thread_id": f"{thread_id}:applied:{second[:8]}"}}
    snapshot = await graph.aget_state(followup)
    assert snapshot.next == ()
    values = snapshot.values
    assert [e["application_id"] for e in values["submitted_applications"]] == [second]
    assert all(r["sent"] for r in values["outreach_sent"])
    # both companies got outreach across the two runs
    assert len(sb.store["outreach"]) == 2
