---
title: Event queue
---

Submit pre-built scenarios by name to observe how the LLM agents react to different event types. No need to construct full JSON payloads — just pick a scenario and the system runs the full pipeline, persists the result, and returns it. {% .lead %}

---

## Why use the event queue?

The analyze endpoints (`/api/analyze` and `/api/analyze/stream`) require a full JSON payload with event type, title, client name, event data, and optional client memory. The event queue provides a shortcut: submit a scenario name and the system expands it into a complete event, then runs it through the full LLM pipeline.

This is useful for:

- **Demos** — Show how agents react to different risk scenarios without hand-crafting payloads. Results are persisted so you can review them in a timeline via `GET /api/conversations` and clear between runs with `DELETE /api/conversations`.
- **Development** — Quickly trigger agent analysis while building frontend features
- **Testing agent behavior** — Observe how real LLM agents handle wire transfers, security alerts, velocity anomalies, and structuring patterns

---

## Available scenarios

| Name | Title | Client | Event Type |
|------|-------|--------|------------|
| `wire_transfer` | $2.4M Wire to Cyprus | Meridian Holdings | wire_transfer |
| `velocity_alert` | 47 Transactions in 3 Minutes | Quantum Dynamics | velocity_alert |
| `security_alert` | New Device Login — Atlas Capital | Atlas Capital | security_alert |
| `cash_deposit` | $9,800 Cash Deposit — Third This Week | Riverside Deli LLC | cash_deposit |

Each scenario includes realistic event data and client memory context. The payloads match the examples in `backend/requests.http`.

---

## Quick start

### List scenarios

```shell
curl http://localhost:3000/api/queue/scenarios
```

### Submit a scenario (sync)

```shell
curl -X POST http://localhost:3000/api/queue \
  -H "Content-Type: application/json" \
  -d '{"scenario": "wire_transfer"}'
```

Returns a `ConversationRecord` with camelCase keys — includes `id`, agents, messages, moderator summary, action items, and client memory. The result is also persisted and retrievable via `GET /api/conversations/{id}`.

### Submit a scenario (SSE stream)

```shell
curl -X POST http://localhost:3000/api/queue/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"scenario": "security_alert"}'
```

Returns SSE events — `start`, `agent_complete` (x3), `moderator_complete`, `done`. The `done` event includes a `conversation_id` for retrieving the persisted result.

---

## Scenario details

### Wire transfer — Meridian Holdings

A $2.4M wire to Bank of Cyprus from a known trade finance client. The transfer is 2x the client's typical monthly volume. Originating IP is a known Tor exit node. Tests how agents handle high-value transfers to higher-risk jurisdictions.

```json
{
  "event_type": "wire_transfer",
  "client_name": "Meridian Holdings",
  "event_data": {
    "amount": 2400000,
    "currency": "USD",
    "destination_country": "CY",
    "destination_bank": "Bank of Cyprus",
    "ip_address": "185.220.101.42"
  }
}
```

### Velocity alert — Quantum Dynamics

47 ACH transactions in 3 minutes totaling $892K. The client is a known payroll processor with a documented monthly batch pattern. Tests how agents distinguish legitimate batch processing from suspicious velocity.

```json
{
  "event_type": "velocity_alert",
  "client_name": "Quantum Dynamics",
  "event_data": {
    "transaction_count": 47,
    "time_window_seconds": 180,
    "total_amount": 892000,
    "transaction_type": "batch_ach"
  }
}
```

### Security alert — Atlas Capital

New device login from Istanbul for a US-based hedge fund. 3 failed attempts in 24 hours preceded the successful login. SMS-based MFA, outdated SDK version. Tests how agents identify account takeover patterns.

```json
{
  "event_type": "security_alert",
  "client_name": "Atlas Capital",
  "event_data": {
    "alert_type": "new_device",
    "ip_address": "91.108.56.130",
    "geo_location": "Istanbul, Turkey",
    "failed_attempts_24h": 3,
    "mfa_method": "sms",
    "sdk_version": "2.9.1"
  }
}
```

### Cash deposit — Riverside Deli LLC

$9,800 cash deposit, the third this week ($9,500 + $9,700 + $9,800 = $29,000). A small restaurant with typical weekly deposits of $3K–$5K. Tests how agents identify structuring patterns below the $10K CTR threshold.

```json
{
  "event_type": "cash_deposit",
  "client_name": "Riverside Deli LLC",
  "event_data": {
    "amount": 9800,
    "deposits_this_week": [
      {"date": "2026-02-27", "amount": 9500},
      {"date": "2026-02-28", "amount": 9700},
      {"date": "2026-03-01", "amount": 9800}
    ],
    "weekly_total": 29000
  }
}
```

---

## Implementation

**File:** `backend/app/agents/scenarios.py` — Four `AnalyzeRequest` Pydantic instances, one per scenario.

**File:** `backend/app/api/queue.py` — Three endpoints that look up scenarios, run the LangGraph pipeline directly, and persist results via `InMemoryConversationStore`. The full pipeline (prepare → 3 agents → moderator) is exercised with the real LLM on every request.

**File:** `backend/app/services/store.py` — In-memory conversation store singleton (dict-backed). Queue submissions are auto-saved. Clear between demos with `DELETE /api/conversations`.

See the [Queue API reference](/docs/api-queue) and [Conversations API](/docs/api-conversations) for full endpoint documentation.
