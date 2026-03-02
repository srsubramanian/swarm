"""Shared state for the LangGraph orchestrator."""

import operator
from typing import Annotated, Any, TypedDict

from app.agents.schemas import AgentAnalysis, ModeratorSynthesis


class SwarmState(TypedDict):
    """State passed through the LangGraph orchestrator.

    The `analyses` field uses an add-reducer so each parallel agent node
    can append its result without overwriting others.
    """

    # Input fields — set by the caller
    event_type: str
    title: str
    client_name: str
    event_data: dict[str, Any]
    client_memory: str

    # Accumulated by agent nodes (fan-out reducer)
    analyses: Annotated[list[AgentAnalysis], operator.add]

    # Set by the moderator node (fan-in)
    moderator_synthesis: ModeratorSynthesis | None
