"""Await decision node — pauses graph for RM input via interrupt."""

from langgraph.types import interrupt

from app.agents.state import SwarmState


async def await_decision(state: SwarmState) -> dict:
    """Pause graph execution for RM decision.

    Calls interrupt() with action item data. The graph will be suspended
    until Command(resume=decision_payload) is called via the decision API.
    """
    synthesis = state["moderator_synthesis"]
    decision = interrupt({
        "action_items": [item.model_dump() for item in synthesis.action_items],
        "status": synthesis.status,
        "risk_level": synthesis.risk_level,
    })
    return {"decision": decision}
