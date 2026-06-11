from __future__ import annotations

import structlog
from orchestrator.state import PipelineState
from orchestrator.nodes import (
    discover_jobs_node,
    score_jobs_node,
    tailor_resume_node,
    find_recruiters_node,
    generate_outreach_node,
    summarize_node,
)

logger = structlog.get_logger()


class MorningGraph:
    """Sequential pipeline: discover → score → tailor → recruiters → outreach → summarize.
    Each node writes to Supabase and handles its own empty-state early-return."""

    async def invoke(self, state: PipelineState) -> PipelineState:
        logger.info("graph.start")
        state = await discover_jobs_node(state)
        state = await score_jobs_node(state)
        state = await tailor_resume_node(state)
        state = await find_recruiters_node(state)
        state = await generate_outreach_node(state)
        state = await summarize_node(state)
        logger.info("graph.complete")
        return state


morning_graph = MorningGraph()
