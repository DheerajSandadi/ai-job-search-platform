"""StateGraph assembly.

Flow (spec §4):

    discover_jobs -> score_jobs -> [score >= gate?]
      YES -> tailor_resume -> await_approval  ~~interrupt~~  [approved?]
               applied  -> find_recruiters -> generate_outreach
                           -> send_outreach -> update_analytics
               rejected -> log_rejection -> update_analytics
               pending  -> await_approval (no-op, interrupts again)
      NO  -> log_skip -> update_analytics

The graph interrupts after ``await_approval`` and persists to sqlite via
AsyncSqliteSaver (langgraph 0.1.19 bundles it; the sync SqliteSaver raises
NotImplementedError for ainvoke). API routes resume runs through
orchestrator.approvals.
"""
from __future__ import annotations

from pathlib import Path

import structlog
from langgraph.graph import END, StateGraph

from core.config import settings
from orchestrator import edges, nodes
from orchestrator.state import PipelineState

logger = structlog.get_logger()


def build_graph(checkpointer):
    """Compile the pipeline StateGraph with the given checkpointer."""
    graph = StateGraph(PipelineState)

    graph.add_node("discover_jobs", nodes.discover_jobs)
    graph.add_node("score_jobs", nodes.score_jobs)
    graph.add_node("tailor_resume", nodes.tailor_resume)
    graph.add_node("await_approval", nodes.await_approval)
    graph.add_node("find_recruiters", nodes.find_recruiters)
    graph.add_node("generate_outreach", nodes.generate_outreach)
    graph.add_node("send_outreach", nodes.send_outreach)
    graph.add_node("update_analytics", nodes.update_analytics)
    graph.add_node("log_skip", nodes.log_skip)
    graph.add_node("log_rejection", nodes.log_rejection)

    graph.set_entry_point("discover_jobs")
    graph.add_edge("discover_jobs", "score_jobs")
    graph.add_conditional_edges(
        "score_jobs", edges.route_after_scoring,
        {"tailor_resume": "tailor_resume", "log_skip": "log_skip"},
    )
    graph.add_conditional_edges(
        "tailor_resume", edges.route_after_tailoring,
        {"await_approval": "await_approval", "log_skip": "log_skip"},
    )
    # Interrupted after await_approval; on resume this router is re-evaluated
    # with the human decisions the API routes wrote into state.
    graph.add_conditional_edges(
        "await_approval", edges.route_after_approval,
        {"find_recruiters": "find_recruiters",
         "log_rejection": "log_rejection",
         "await_approval": "await_approval"},
    )
    graph.add_edge("find_recruiters", "generate_outreach")
    graph.add_edge("generate_outreach", "send_outreach")
    graph.add_edge("send_outreach", "update_analytics")
    graph.add_edge("log_skip", "update_analytics")
    graph.add_edge("log_rejection", "update_analytics")
    graph.add_edge("update_analytics", END)

    return graph.compile(checkpointer=checkpointer, interrupt_after=["await_approval"])


_compiled = None


def get_graph():
    """Process-wide compiled graph backed by the sqlite checkpointer.

    Lazy so importing this module never touches the filesystem (tests build
    their own graph with MemorySaver via build_graph)."""
    global _compiled
    if _compiled is None:
        from langgraph.checkpoint.aiosqlite import AsyncSqliteSaver

        db_path = Path(settings.ORCHESTRATOR_CHECKPOINT_DB)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _compiled = build_graph(AsyncSqliteSaver.from_conn_string(str(db_path)))
        logger.info("graph.compiled", checkpoint_db=str(db_path))
    return _compiled
