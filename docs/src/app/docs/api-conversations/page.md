---
title: Conversations API
---

The conversations endpoints let you list, retrieve, and clear persisted conversation records. Queue submissions are auto-saved; analyze endpoints remain stateless. {% .lead %}

---

## How persistence works

When you submit a scenario via `POST /api/queue` or `POST /api/queue/stream`, the system runs the full LLM pipeline, then saves the result as a `ConversationRecord` in an in-memory store. The record includes the complete conversation shape that the frontend expects — agents, messages, moderator summary, action items, and client memory — all with camelCase JSON keys.

The `POST /api/analyze` endpoints remain stateless and do **not** persist anything.

{% callout type="warning" title="In-memory storage" %}
The conversation store lives in process memory. Restarting the app or the Docker container clears all stored conversations. This is intentional for demo use — a database-backed store will replace it when SQLAlchemy models are added.
{% /callout %}

---

## GET /api/conversations

List all stored conversations, newest first.

### Request

```shell
GET /api/conversations
```

### Response

```json
[
  {
    "id": "a1b2c3d4-...",
    "title": "$2.4M Wire to Cyprus",
    "clientName": "Meridian Holdings",
    "riskLevel": "high",
    "status": "awaiting_decision",
    "eventType": "wire_transfer",
    "startedAt": "2026-03-02T12:34:56+00:00",
    "messageCount": 3,
    "agents": [...],
    "messages": [...],
    "moderatorSummary": {...},
    "actionRequired": {...},
    "clientMemory": {...}
  }
]
```

Returns an empty array `[]` if no conversations have been submitted.

---

## GET /api/conversations/{id}

Retrieve a single conversation by its UUID.

### Request

```shell
GET /api/conversations/a1b2c3d4-...
```

### Response

Returns the full `ConversationRecord` JSON (same shape as a single item in the list response).

### Errors

| Status | Description |
|--------|-------------|
| 404 | Conversation not found |

---

## DELETE /api/conversations

Clear all stored conversations. Useful for resetting between demo runs.

### Request

```shell
DELETE /api/conversations
```

### Response

```json
{
  "cleared": 2
}
```

The `cleared` field indicates how many conversations were removed.

---

## ConversationRecord schema

The response shape matches the frontend `Conversation` TypeScript interface. All field names use camelCase in JSON output (Pydantic alias generation).

```python
class ConversationRecord:
    id: str                    # UUID
    title: str
    clientName: str
    riskLevel: str             # "critical" | "high" | "medium" | "low"
    status: str                # "awaiting_decision" | "concluded"
    eventType: str
    startedAt: str             # ISO 8601 UTC
    messageCount: int
    agents: list[AgentInfoRecord]
    messages: list[MessageRecord]
    moderatorSummary: ModeratorSummaryRecord
    actionRequired: ActionRequiredRecord
    clientMemory: ClientMemoryRecord
    decision: DecisionRecord | None  # Present after RM decision
```

### Nested models

**AgentInfoRecord** — One per agent (compliance, security, engineering):

| Field | Type | Description |
|-------|------|-------------|
| `role` | string | Agent role |
| `name` | string | Display name (e.g. "Compliance Analyst") |
| `status` | string | Always "complete" for persisted records |
| `position` | string | One-sentence position statement |

**MessageRecord** — One per agent analysis:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID |
| `agentRole` | string | Agent role |
| `agentName` | string | Display name |
| `content` | string | Full analysis markdown |
| `timestamp` | string | ISO 8601 UTC |

**ModeratorSummaryRecord** — Synthesized from moderator output:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | e.g. "HOLD RECOMMENDED" |
| `consensus` | string | Where agents agree (includes dissent if any) |
| `keyDecisions` | string[] | Most important findings |
| `riskAssessment` | string | Risk justification |
| `nextSteps` | string[] | Concrete next steps |

**ActionRequiredRecord** — Action items from the moderator:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "pending" or "actioned" |
| `options` | ActionOptionRecord[] | Available actions |
| `actionedOption` | string? | null until RM acts, then the selected option ID |

**DecisionRecord** — Present after an RM decision (via [Decisions API](/docs/api-decisions)):

| Field | Type | Description |
|-------|------|-------------|
| `optionId` | string | Selected action option ID |
| `action` | string | "approve", "reject", or "escalate" |
| `justification` | string | RM's rationale (required for escalate) |
| `decidedAt` | string | ISO 8601 UTC |

**ClientMemoryRecord** — Client context passed to agents:

| Field | Type | Description |
|-------|------|-------------|
| `clientName` | string | Client name |
| `content` | string | Memory markdown |
| `lastUpdated` | string | ISO 8601 UTC |

---

## Examples

### Demo workflow

```shell
# 1. Submit two scenarios
curl -X POST localhost:3000/api/queue \
  -H "Content-Type: application/json" \
  -d '{"scenario":"wire_transfer"}'

curl -X POST localhost:3000/api/queue \
  -H "Content-Type: application/json" \
  -d '{"scenario":"security_alert"}'

# 2. List conversations (newest first)
curl localhost:3000/api/conversations

# 3. Get a specific conversation by ID
curl localhost:3000/api/conversations/{id-from-step-1}

# 4. Reset between demos
curl -X DELETE localhost:3000/api/conversations

# 5. Verify empty
curl localhost:3000/api/conversations
# → []
```

### Verify analyze is stateless

```shell
# Analyze does NOT persist
curl -X POST localhost:3000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"event_type":"wire_transfer","title":"Test","client_name":"Test","event_data":{"amount":100}}'

curl localhost:3000/api/conversations
# → [] (analyze doesn't persist)
```

---

## Implementation

**File:** `backend/app/api/history.py` — Three endpoints (list, get, clear) using the shared store singleton.

**File:** `backend/app/services/store.py` — `InMemoryConversationStore` with `save()`, `get()`, `list_all()`, and `clear()` methods. Dict-backed, thread-safe via GIL.

**File:** `backend/app/services/conversation_builder.py` — `build_conversation()` maps graph output (`AnalyzeRequest` + `AgentAnalysis[]` + `ModeratorSynthesis`) into a `ConversationRecord`.

**File:** `backend/app/schemas/conversations.py` — Pydantic models with `alias_generator=to_camel` for camelCase JSON output matching the frontend TypeScript types.
