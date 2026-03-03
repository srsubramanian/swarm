"""LangGraph orchestrator — triage, fan-out 3 agents, fan-in to moderator, interrupt for RM decision."""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes.await_decision import await_decision
from app.agents.nodes.compliance import compliance_agent
from app.agents.nodes.engineering import engineering_agent
from app.agents.nodes.moderator import moderator_node
from app.agents.nodes.notify import notify_rm
from app.agents.nodes.post_decision import post_decision
from app.agents.nodes.prepare import prepare_context
from app.agents.nodes.security import security_agent
from app.agents.nodes.triage import triage_edge, triage_router
from app.agents.state import SwarmState

# Shared in-memory checkpointer for stateful graph runs
_saver = InMemorySaver()


def build_graph(checkpointer=_saver, include_triage=True):
    """Build and compile the SwarmOps orchestrator graph.

    Full topology (with triage):
        START → prepare → triage → (conditional)
            ├─ "respond"  → [compliance | security | engineering] → moderator → await_decision → post_decision → END
            ├─ "notify"   → notify_rm → END
            └─ "ignore"   → END

    Without triage (queue/analyze endpoints — all events get full processing):
        START → prepare → [compliance | security | engineering] → moderator → await_decision → post_decision → END

    Args:
        checkpointer: LangGraph checkpointer for state persistence.
            Pass None for stateless mode (no interrupt support).
        include_triage: If True, adds triage node with conditional routing.
            The triage_edge uses Send() for fan-out to 3 agents when classification is "respond".
    """
    builder = StateGraph(SwarmState)

    # Add all nodes
    builder.add_node("prepare", prepare_context)
    builder.add_node("compliance", compliance_agent)
    builder.add_node("security", security_agent)
    builder.add_node("engineering", engineering_agent)
    builder.add_node("moderator", moderator_node)
    builder.add_node("await_decision", await_decision)
    builder.add_node("post_decision", post_decision)

    # Edges: START → prepare
    builder.add_edge(START, "prepare")

    if include_triage:
        builder.add_node("triage", triage_router)
        builder.add_node("notify_rm", notify_rm)

        builder.add_edge("prepare", "triage")
        # triage_edge returns Send() list for fan-out or string for single node
        builder.add_conditional_edges("triage", triage_edge)
        builder.add_edge("notify_rm", END)
    else:
        # Direct fan-out (no triage)
        builder.add_edge("prepare", "compliance")
        builder.add_edge("prepare", "security")
        builder.add_edge("prepare", "engineering")

    # Fan-in: all agents → moderator
    builder.add_edge("compliance", "moderator")
    builder.add_edge("security", "moderator")
    builder.add_edge("engineering", "moderator")

    # Decision flow: moderator → await_decision → post_decision → END
    builder.add_edge("moderator", "await_decision")
    builder.add_edge("await_decision", "post_decision")
    builder.add_edge("post_decision", END)

    return builder.compile(checkpointer=checkpointer)


# Stateful graph for /api/queue (supports interrupt/resume, no triage)
graph = build_graph(checkpointer=_saver, include_triage=False)

# Stateless graph for /api/analyze (no checkpoint, no interrupt, no triage)
stateless_graph = build_graph(checkpointer=None, include_triage=False)

# Event processing graph (with triage + checkpointing for webhook/simulator)
event_graph = build_graph(checkpointer=_saver, include_triage=True)
