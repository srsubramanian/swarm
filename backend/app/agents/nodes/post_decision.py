"""Post-decision node — records RM decision and proposes memory updates."""

import json
import logging
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm import get_llm
from app.agents.state import SwarmState
from app.services.memory_store import memory_store

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "memory_update.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _format_context(state: SwarmState) -> str:
    """Format event + analyses + decision for the memory update LLM call."""
    parts = [
        f"## Event: {state['event_type']}",
        f"**Title:** {state['title']}",
        f"**Client:** {state['client_name']}",
        "",
        "### Event Data",
        "```json",
        json.dumps(state["event_data"], indent=2, default=str),
        "```",
    ]

    if state.get("client_memory"):
        parts.extend(["", "### Existing Client Memory", state["client_memory"]])

    parts.extend(["", "### Agent Analyses"])
    for analysis in state.get("analyses", []):
        data = analysis.model_dump() if hasattr(analysis, "model_dump") else analysis
        parts.extend([
            f"\n**{data['agent_role'].title()}:** {data['position']}",
            f"Risk: {data['risk_level']}, Confidence: {data['confidence']}",
        ])

    synthesis = state.get("moderator_synthesis")
    if synthesis:
        data = synthesis.model_dump() if hasattr(synthesis, "model_dump") else synthesis
        parts.extend([
            "",
            "### Moderator Synthesis",
            f"**Status:** {data['status']}",
            f"**Risk:** {data['risk_level']}",
            f"**Consensus:** {data['consensus']}",
        ])

    decision = state.get("decision")
    if decision:
        parts.extend([
            "",
            "### RM Decision",
            f"**Action:** {decision.get('action', 'unknown')}",
            f"**Justification:** {decision.get('justification', 'none provided')}",
        ])

    return "\n".join(parts)


async def post_decision(state: SwarmState) -> dict:
    """Process the RM decision and propose a memory update.

    1. Logs the decision
    2. Calls LLM to propose a memory update based on the full context
    3. Saves the proposal as pending in the memory store
    """
    decision = state.get("decision")
    if decision:
        logger.info(
            "RM decision recorded: action=%s, option_id=%s",
            decision.get("action"),
            decision.get("option_id"),
        )

    # Propose memory update via LLM
    try:
        llm = get_llm()
        context = _format_context(state)
        messages = [
            SystemMessage(content=_load_prompt()),
            HumanMessage(content=context),
        ]
        response = await llm.ainvoke(messages)
        proposed_content = response.content

        if proposed_content and proposed_content.strip():
            proposal_id = memory_store.propose_update(
                client_name=state["client_name"],
                proposed_content=proposed_content.strip(),
            )
            logger.info(
                "Memory update proposed for %s: proposal_id=%s",
                state["client_name"],
                proposal_id,
            )
            return {"memory_update_proposal": {"proposal_id": proposal_id, "content": proposed_content.strip()}}
    except Exception:
        logger.exception("Failed to propose memory update for %s", state["client_name"])

    return {}
