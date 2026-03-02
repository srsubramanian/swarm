"""LangGraph orchestrator — fan-out 3 agents, fan-in to moderator."""

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.compliance import compliance_agent
from app.agents.nodes.engineering import engineering_agent
from app.agents.nodes.moderator import moderator_node
from app.agents.nodes.prepare import prepare_context
from app.agents.nodes.security import security_agent
from app.agents.state import SwarmState


def build_graph() -> StateGraph:
    """Build and compile the SwarmOps orchestrator graph.

    Topology: START → prepare → [compliance | security | engineering] → moderator → END
    """
    builder = StateGraph(SwarmState)

    # Add nodes
    builder.add_node("prepare", prepare_context)
    builder.add_node("compliance", compliance_agent)
    builder.add_node("security", security_agent)
    builder.add_node("engineering", engineering_agent)
    builder.add_node("moderator", moderator_node)

    # Edges: START → prepare
    builder.add_edge(START, "prepare")

    # Fan-out: prepare → 3 agents in parallel
    builder.add_edge("prepare", "compliance")
    builder.add_edge("prepare", "security")
    builder.add_edge("prepare", "engineering")

    # Fan-in: all agents → moderator
    builder.add_edge("compliance", "moderator")
    builder.add_edge("security", "moderator")
    builder.add_edge("engineering", "moderator")

    # moderator → END
    builder.add_edge("moderator", END)

    return builder.compile()


# Module-level singleton
graph = build_graph()
