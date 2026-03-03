---
title: Decisions API
---

The decisions endpoint lets an RM submit a decision (approve, reject, escalate) on a conversation that is awaiting action. It resumes the paused LangGraph pipeline and records the outcome. {% .lead %}

---

## How it works

When a scenario is submitted via `POST /api/queue`, the LangGraph pipeline runs through agents and moderator, then **pauses** at the `await_decision` node using LangGraph's `interrupt()`. The conversation is persisted with status `awaiting_decision`.

When the RM submits a decision via this endpoint, the graph resumes from the interrupt point using `Command(resume=payload)`. The `post_decision` node records the outcome, proposes a client memory update, and the conversation transitions to `concluded`.

```shell
Queue submit → agents → moderator → await_decision (interrupt)
                                          ↓
                              RM reviews action items
                                          ↓
                              POST /api/decisions/{id}
                                          ↓
                              Command(resume=payload)
                                          ↓
                              post_decision → END
```

---

## POST /api/decisions/{conversation_id}

Submit an RM decision on a conversation.

### Request

```shell
POST /api/decisions/{conversation_id}
Content-Type: application/json
```

```json
{
  "option_id": "opt-1",
  "action": "approve",
  "justification": "Cleared after compliance review"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `option_id` | string | Yes | ID of the selected action option from `actionRequired.options` |
| `action` | string | Yes | One of: `approve`, `reject`, `escalate` |
| `justification` | string | No | Required for `escalate` actions; optional for others |

### Response

Returns the updated `ConversationRecord` with status `concluded`:

```json
{
  "id": "a1b2c3d4-...",
  "status": "concluded",
  "actionRequired": {
    "status": "actioned",
    "options": [...],
    "actionedOption": "opt-1"
  },
  "decision": {
    "optionId": "opt-1",
    "action": "approve",
    "justification": "Cleared after compliance review",
    "decidedAt": "2026-03-02T12:45:00+00:00"
  }
}
```

### Errors

| Status | Description |
|--------|-------------|
| 404 | Conversation not found or no thread mapping exists |
| 400 | Conversation already concluded |

---

## DecisionRecord schema

Added to `ConversationRecord` after an RM decision:

```python
class DecisionRecord(_CamelModel):
    option_id: str         # → optionId
    action: str            # "approve" | "reject" | "escalate"
    justification: str
    decided_at: str        # → decidedAt (ISO 8601 UTC)
```

---

## LangGraph interrupt/resume

The decision flow relies on two LangGraph primitives:

### interrupt()

Called in the `await_decision` node to pause graph execution:

```python
from langgraph.types import interrupt

async def await_decision(state: SwarmState) -> dict:
    synthesis = state["moderator_synthesis"]
    decision = interrupt({
        "action_items": [item.model_dump() for item in synthesis.action_items],
        "status": synthesis.status,
        "risk_level": synthesis.risk_level,
    })
    return {"decision": decision}
```

### Command(resume=)

Used by the API endpoint to resume the graph with the RM's decision:

```python
from langgraph.types import Command

result = await graph.ainvoke(
    Command(resume=decision_payload),
    config={"configurable": {"thread_id": thread_id}}
)
```

### Checkpointing

The interrupt/resume pattern requires a **checkpointer** to persist graph state between the pause and resume. SwarmOps uses `InMemorySaver`:

```python
from langgraph.checkpoint.memory import InMemorySaver

_saver = InMemorySaver()
graph = build_graph(checkpointer=_saver)
```

Each conversation is assigned a unique `thread_id` that maps to its `conversation_id`. The `ThreadStore` manages this mapping.

---

## Examples

### Submit a decision

```shell
# 1. Submit a scenario (returns conversation with status "awaiting_decision")
CONV_ID=$(curl -s -X POST localhost:3000/api/queue \
  -H "Content-Type: application/json" \
  -d '{"scenario": "wire_transfer"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 2. Submit a decision
curl -X POST "localhost:3000/api/decisions/$CONV_ID" \
  -H "Content-Type: application/json" \
  -d '{"option_id": "opt-1", "action": "approve", "justification": "Cleared after review"}'
```

---

## Implementation

**File:** `backend/app/api/decisions.py` — Decision endpoint that resumes the interrupted graph.

**File:** `backend/app/agents/nodes/await_decision.py` — Node that calls `interrupt()` to pause the graph.

**File:** `backend/app/agents/nodes/post_decision.py` — Node that processes the resumed decision, proposes memory updates.

**File:** `backend/app/services/store.py` — `ThreadStore` maps `conversation_id` to `thread_id` for graph resume.
