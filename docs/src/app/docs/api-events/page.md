---
title: Events API
---

The events endpoints accept external events via webhook and provide a built-in event simulator for demo purposes. Events are processed through the full pipeline including triage classification. {% .lead %}

---

## POST /api/events/webhook

Accept an external event and process it through the full pipeline (triage + agents + moderator + decision pause).

### Request

```shell
POST /api/events/webhook
Content-Type: application/json
```

```json
{
  "event_type": "wire_transfer",
  "title": "$500K Wire to Malta",
  "client_name": "Oceanic Trading LLC",
  "event_data": {
    "amount": 500000,
    "currency": "USD",
    "destination_country": "MT"
  },
  "client_memory": ""
}
```

The request body matches the `AnalyzeRequest` schema used by `/api/analyze`.

### Response

Returns the `ConversationRecord` with status `awaiting_decision` (if triaged as `respond`) or a notification result (if triaged as `notify`).

### Triage behavior

Webhook events go through the **event graph** which includes a triage router:

- **respond** — Full agent pipeline runs (compliance + security + engineering + moderator + decision pause)
- **notify** — Lightweight notification recorded, no full analysis
- **ignore** — Event discarded, minimal response returned

---

## POST /api/events/simulate/start

Start the built-in event simulator. Generates random events at a configurable interval.

### Request

```shell
POST /api/events/simulate/start
```

### Response

```json
{
  "status": "started"
}
```

### Errors

| Status | Description |
|--------|-------------|
| 400 | Simulator already running |

---

## POST /api/events/simulate/stop

Stop the event simulator.

### Request

```shell
POST /api/events/simulate/stop
```

### Response

```json
{
  "status": "stopped"
}
```

### Errors

| Status | Description |
|--------|-------------|
| 400 | Simulator not running |

---

## Event simulator

The `EventSimulator` generates demo events on a configurable interval using asyncio:

```python
class EventSimulator:
    def __init__(self, interval_seconds: float = 30.0):
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self): ...   # Creates asyncio task
    async def stop(self): ...    # Cancels task

    @property
    def running(self) -> bool: ...
```

The simulator randomly selects from the 4 built-in scenarios and submits them through the event graph (with triage). It's designed for demo use — real production would use the webhook endpoint with external event sources.

The simulator is automatically stopped during application shutdown via the FastAPI lifespan handler.

---

## Implementation

**File:** `backend/app/api/events.py` — Webhook and simulator endpoints.

**File:** `backend/app/services/event_source.py` — `EventSimulator` with asyncio task management.

**File:** `backend/app/agents/nodes/triage.py` — Triage classification node used by the event graph.

**File:** `backend/app/agents/orchestrator.py` — `event_graph` variant includes triage routing.
