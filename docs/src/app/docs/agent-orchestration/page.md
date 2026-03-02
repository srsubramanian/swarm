---
title: Agent orchestration
---

SwarmOps uses LangGraph's `StateGraph` to orchestrate three domain agents in a fan-out/fan-in topology. {% .lead %}

---

## LangGraph StateGraph

The orchestrator is defined in `backend/app/agents/orchestrator.py`:

```python
from langgraph.graph import END, START, StateGraph

def build_graph() -> StateGraph:
    builder = StateGraph(SwarmState)

    # Add nodes
    builder.add_node("prepare", prepare_context)
    builder.add_node("compliance", compliance_agent)
    builder.add_node("security", security_agent)
    builder.add_node("engineering", engineering_agent)
    builder.add_node("moderator", moderator_node)

    # START → prepare
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
```

The graph is compiled once at import time and reused across all requests.

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
```

Agents read from the input fields and write to `analyses`. The moderator reads `analyses` and writes `moderator_synthesis`.

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
