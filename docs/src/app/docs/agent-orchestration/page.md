---
title: Agent orchestration
---

SwarmOps uses LangGraph's `StateGraph` to orchestrate three domain agents in a fan-out/fan-in topology. {% .lead %}

---

## LangGraph StateGraph

The orchestrator is defined in `backend/app/agents/orchestrator.py`. It supports three graph variants via a parameterized `build_graph()` function:

```python
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver

_saver = InMemorySaver()

def build_graph(checkpointer=_saver, include_triage=False):
    builder = StateGraph(SwarmState)

    # Core nodes
    builder.add_node("prepare", prepare_context)
    builder.add_node("compliance", compliance_agent)
    builder.add_node("security", security_agent)
    builder.add_node("engineering", engineering_agent)
    builder.add_node("moderator", moderator_node)
    builder.add_node("await_decision", await_decision)
    builder.add_node("post_decision", post_decision)

    builder.add_edge(START, "prepare")

    if include_triage:
        builder.add_node("triage", triage_router)
        builder.add_node("notify_rm", notify_rm_node)
        builder.add_edge("prepare", "triage")
        builder.add_conditional_edges("triage", triage_edge)
    else:
        # Direct fan-out from prepare
        builder.add_edge("prepare", "compliance")
        builder.add_edge("prepare", "security")
        builder.add_edge("prepare", "engineering")

    # Fan-in + decision pipeline
    builder.add_edge("compliance", "moderator")
    builder.add_edge("security", "moderator")
    builder.add_edge("engineering", "moderator")
    builder.add_edge("moderator", "await_decision")
    builder.add_edge("await_decision", "post_decision")
    builder.add_edge("post_decision", END)

    return builder.compile(checkpointer=checkpointer)

# Three graph variants
graph = build_graph(checkpointer=_saver, include_triage=False)
stateless_graph = build_graph(checkpointer=None, include_triage=False)
event_graph = build_graph(checkpointer=_saver, include_triage=True)
```

Each variant is compiled once at import time and reused across all requests.

| Graph | Checkpointer | Triage | Used by |
|-------|-------------|--------|---------|
| `stateless_graph` | None | No | `/api/analyze` (stateless) |
| `graph` | `InMemorySaver` | No | `/api/queue` (interrupt/resume) |
| `event_graph` | `InMemorySaver` | Yes | `/api/events/webhook`, simulator |

---

## Fan-out / fan-in

**Fan-out** means three edges leave the `prepare` node simultaneously. LangGraph runs the compliance, security, and engineering agents in parallel — they don't wait for each other.

**Fan-in** means the moderator node has three incoming edges. LangGraph waits for all three agents to complete before executing the moderator.

This is possible because the shared state uses an **add-reducer** on the `analyses` field:

```python
analyses: Annotated[list[AgentAnalysis], operator.add]
```

Each agent appends its `AgentAnalysis` to the list. The reducer merges them without conflicts, regardless of completion order.

---

## Shared state

The `SwarmState` TypedDict is the single data structure passed through the graph:

```python
class SwarmState(TypedDict):
    # Input
    event_type: str
    title: str
    client_name: str
    event_data: dict[str, Any]
    client_memory: str

    # Accumulated by agents
    analyses: Annotated[list[AgentAnalysis], operator.add]

    # Set by moderator
    moderator_synthesis: ModeratorSynthesis | None

    # RM decision (populated by Command(resume=) after interrupt)
    decision: dict | None

    # Memory update proposal from post_decision
    memory_update_proposal: dict | None

    # Triage classification ("respond" | "notify" | "ignore")
    triage_result: str | None
```

Agents read from the input fields and write to `analyses`. The moderator reads `analyses` and writes `moderator_synthesis`. The `await_decision` node pauses the graph and receives the RM's decision via `Command(resume=)`. The `post_decision` node reads the decision and proposes memory updates.

---

## Execution modes

### Synchronous

```python
result = await graph.ainvoke(input_state)
# result["analyses"] → list of 3 AgentAnalysis
# result["moderator_synthesis"] → ModeratorSynthesis
```

### Streaming

```python
async for event in graph.astream(input_state, stream_mode="updates"):
    for node_name, node_output in event.items():
        # Each agent emits as it completes
```

The streaming mode powers the SSE endpoint, emitting results to the client as each agent finishes rather than waiting for the full pipeline.

---

## Retry handling

Because three agents call Bedrock simultaneously, throttling is common. The LLM client uses adaptive retry with up to 8 attempts:

```python
BotoConfig(retries={"max_attempts": 8, "mode": "adaptive"})
```

This handles transient `ThrottlingException` errors without failing the graph.
