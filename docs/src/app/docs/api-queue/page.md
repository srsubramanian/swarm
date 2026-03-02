---
title: Queue API
---

The queue endpoints let you submit pre-built scenarios by name instead of constructing full JSON payloads. They delegate to the existing analyze endpoints, so the full pipeline is exercised. {% .lead %}

---

## GET /api/queue/scenarios

List all available scenarios with metadata.

### Request

```shell
GET /api/queue/scenarios
```

### Response

```json
[
  {
    "name": "wire_transfer",
    "title": "$2.4M Wire to Cyprus",
    "client_name": "Meridian Holdings",
    "event_type": "wire_transfer"
  },
  {
    "name": "velocity_alert",
    "title": "47 Transactions in 3 Minutes — Quantum Dynamics",
    "client_name": "Quantum Dynamics",
    "event_type": "velocity_alert"
  },
  {
    "name": "security_alert",
    "title": "New Device Login — Atlas Capital",
    "client_name": "Atlas Capital",
    "event_type": "security_alert"
  },
  {
    "name": "cash_deposit",
    "title": "$9,800 Cash Deposit — Third This Week",
    "client_name": "Riverside Deli LLC",
    "event_type": "cash_deposit"
  }
]
```

---

## POST /api/queue

Submit a scenario by name and receive the full synchronous result. Delegates to `POST /api/analyze`.

### Request

```shell
POST /api/queue
Content-Type: application/json
```

```json
{
  "scenario": "wire_transfer"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scenario` | string | Yes | Scenario name from `/api/queue/scenarios` |

### Response

Same as [POST /api/analyze](/docs/api-analyze) — contains `agents` array (3 agent analyses) and `moderator_summary`.

### Errors

| Status | Description |
|--------|-------------|
| 404 | Unknown scenario name. Response includes available scenarios. |

```json
{
  "detail": "Unknown scenario 'nonexistent'. Available: ['wire_transfer', 'velocity_alert', 'security_alert', 'cash_deposit']"
}
```

---

## POST /api/queue/stream

Submit a scenario by name and receive an SSE stream. Delegates to `POST /api/analyze/stream`.

### Request

```shell
POST /api/queue/stream
Content-Type: application/json
Accept: text/event-stream
```

```json
{
  "scenario": "security_alert"
}
```

### Response

Same SSE event sequence as [POST /api/analyze/stream](/docs/api-analyze-stream):

1. `start` — Processing has begun
2. `agent_complete` (x3) — Each agent finishes (order varies)
3. `moderator_complete` — Synthesis is ready
4. `done` — Stream complete

Agents complete at LLM speed — typically the three agents finish within a few seconds of each other, followed by the moderator synthesis.

### Errors

| Status | Description |
|--------|-------------|
| 404 | Unknown scenario name |

---

## Available scenarios

| Name | Event Type | Client | Risk | Pattern |
|------|-----------|--------|------|---------|
| `wire_transfer` | wire_transfer | Meridian Holdings | critical | Full consensus — all agents recommend HOLD |
| `velocity_alert` | velocity_alert | Quantum Dynamics | medium | Split — Compliance flags, Security+Engineering clear |
| `security_alert` | security_alert | Atlas Capital | high | Security drives — critical ATO concern |
| `cash_deposit` | cash_deposit | Riverside Deli LLC | high | Strong consensus — textbook structuring |

Each scenario uses the exact same event payload as the corresponding example in `backend/requests.http`.

---

## Examples

### List scenarios

```shell
curl http://localhost:3000/api/queue/scenarios
```

### Sync — wire transfer

```shell
curl -X POST http://localhost:3000/api/queue \
  -H "Content-Type: application/json" \
  -d '{"scenario": "wire_transfer"}'
```

### SSE stream — security alert

```shell
curl -X POST http://localhost:3000/api/queue/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"scenario": "security_alert"}'
```

### Each scenario (sync)

```shell
for s in wire_transfer velocity_alert security_alert cash_deposit; do
  echo "=== $s ==="
  curl -s -X POST http://localhost:3000/api/queue \
    -H "Content-Type: application/json" \
    -d "{\"scenario\": \"$s\"}" | python3 -m json.tool | head -5
  echo
done
```

---

## Implementation

**File:** `backend/app/api/queue.py`

The queue router defines three endpoints that look up scenarios from `backend/app/agents/scenarios.py` and delegate to the existing `analyze()` and `analyze_stream()` functions in `backend/app/api/conversations.py`. No separate code paths — the full LangGraph pipeline is exercised.

**File:** `backend/app/agents/scenarios.py`

Four `AnalyzeRequest` Pydantic instances, one per scenario, with complete event data matching the payloads in `backend/requests.http`.
