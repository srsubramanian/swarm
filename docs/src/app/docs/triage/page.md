---
title: Triage router
---

The triage router classifies incoming events before deciding whether to run the full agent pipeline. It uses a lightweight LLM call to categorize events as `respond`, `notify`, or `ignore`. {% .lead %}

---

## Classification

The triage node runs a single LLM call with structured output to classify events:

| Classification | Action | Use case |
|---------------|--------|----------|
| `respond` | Full agent pipeline | High-value transactions, security alerts, compliance triggers |
| `notify` | Lightweight notification to RM | Routine events that need visibility but not full analysis |
| `ignore` | Discard | Low-priority events, duplicates, system noise |

---

## Implementation

**File:** `backend/app/agents/nodes/triage.py`

```python
class TriageResult(BaseModel):
    classification: str  # "respond" | "notify" | "ignore"
    reason: str          # Brief explanation

async def triage_router(state: SwarmState) -> dict:
    llm = get_llm()
    prompt = _load_prompt()  # prompts/triage.md
    structured_llm = llm.with_structured_output(TriageResult)
    messages = [SystemMessage(content=prompt), HumanMessage(content=_format_event(state))]
    result = await structured_llm.ainvoke(messages)
    return {"triage_result": result.classification}
```

### Conditional edge

The triage result drives a conditional edge in the graph:

```python
def triage_edge(state: SwarmState) -> Union[str, list[Send]]:
    classification = state.get("triage_result", "respond")
    if classification == "respond":
        return [Send("compliance", state), Send("security", state), Send("engineering", state)]
    elif classification == "notify":
        return "notify_rm"
    else:
        return "__end__"
```

The `respond` path uses `Send()` objects for conditional fan-out to all three agents. The `notify` path routes to a lightweight notification node. The `ignore` path goes directly to END.

---

## Event graph topology

The triage router is only included in the **event graph** (used for webhooks and the event simulator). The standard queue graph skips triage.

```shell
START → prepare → triage → (conditional)
                    ├─ "respond"  → [compliance | security | engineering] → moderator → await_decision → post_decision → END
                    ├─ "notify"   → notify_rm → END
                    └─ "ignore"   → END
```

---

## Prompt template

**File:** `backend/app/agents/prompts/triage.md`

The triage prompt instructs the LLM to classify events based on:
- Event type and severity
- Amount thresholds
- Client risk profile
- Regulatory trigger conditions

The prompt is designed for fast classification — it doesn't require tool calls or deep analysis.

---

## Graph variants

SwarmOps maintains three graph variants:

| Graph | Triage | Checkpointer | Used by |
|-------|--------|--------------|---------|
| `stateless_graph` | No | None | `/api/analyze` (stateless) |
| `graph` | No | `InMemorySaver` | `/api/queue` (stateful, interrupt) |
| `event_graph` | Yes | `InMemorySaver` | `/api/events/webhook`, simulator |
