---
title: Quick start
---

Get SwarmOps running locally and send your first event in under five minutes. {% .lead %}

---

## Prerequisites

- Docker and Docker Compose
- AWS credentials configured (`~/.aws/credentials` or environment variables) with Bedrock access
- `curl` or an HTTP client (VS Code REST Client, Postman, etc.)

---

## Start the stack

```shell
git clone <your-repo-url> swarmops
cd swarmops
docker compose up --build -d
```

This starts three services:

| Service | Port | Description |
|---------|------|-------------|
| **app** | 3000 | nginx reverse proxy — frontend + backend |
| **postgres** | 5432 | PostgreSQL with pgvector extension |
| **redis** | 6379 | Redis for cache and pub/sub |

Check that everything is healthy:

```shell
curl http://localhost:3000/health
# {"status":"ok"}
```

---

## Send your first event

Submit a wire transfer for analysis:

```shell
curl -X POST http://localhost:3000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "wire_transfer",
    "title": "$2.4M Wire to Cyprus",
    "client_name": "Meridian Holdings",
    "event_data": {
      "amount": 2400000,
      "currency": "USD",
      "destination_country": "CY",
      "destination_bank": "Bank of Cyprus",
      "reference": "INV-2024-0847"
    },
    "client_memory": "Known client since 2019. Regular EU transfers for trade finance."
  }'
```

The response contains analyses from all three agents plus a moderator synthesis with action items.

---

## Try SSE streaming

For real-time updates as each agent completes:

```shell
curl -X POST http://localhost:3000/api/analyze/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "event_type": "wire_transfer",
    "title": "$2.4M Wire to Cyprus",
    "client_name": "Meridian Holdings",
    "event_data": {
      "amount": 2400000,
      "currency": "USD",
      "destination_country": "CY"
    }
  }'
```

You'll see SSE events in this order:

1. `start` — Processing has begun
2. `agent_complete` (x3) — Each agent finishes (order varies)
3. `moderator_complete` — Synthesis is ready
4. `done` — Stream complete

---

## Use the event queue (shortcut)

Instead of constructing full JSON payloads, submit pre-built scenarios by name:

```shell
# List available scenarios
curl http://localhost:3000/api/queue/scenarios

# Submit a scenario (sync)
curl -X POST http://localhost:3000/api/queue \
  -H "Content-Type: application/json" \
  -d '{"scenario": "wire_transfer"}'

# Submit a scenario (SSE stream)
curl -X POST http://localhost:3000/api/queue/stream \
  -H "Content-Type: application/json" \
  -d '{"scenario": "security_alert"}'
```

Four scenarios are available: `wire_transfer`, `velocity_alert`, `security_alert`, `cash_deposit`. See the [Queue API reference](/docs/api-queue) for details.

---

## Switch the LLM model

By default SwarmOps uses Claude Haiku 4.5 on Bedrock. To use a different model:

```shell
SWARM_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0 docker compose up -d
```

See [Configuration](/docs/configuration) for all available environment variables.

---

## Stop the stack

```shell
docker compose down
```

Add `-v` to also remove the Postgres data volume:

```shell
docker compose down -v
```

---

## Next steps

- [System overview](/docs/system-overview) — Understand the full architecture
- [API reference](/docs/api-analyze) — Explore request/response schemas
- [Event queue](/docs/event-queue) — Submit scenarios by name to observe agent reactions
- [Development guide](/docs/development) — Run backend and frontend locally without Docker
