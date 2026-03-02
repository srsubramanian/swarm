---
title: System overview
---

SwarmOps follows a simple pipeline: business events enter, three AI agents analyze them in parallel, a moderator synthesizes the results, and a human Relationship Manager makes the final call. {% .lead %}

---

## The core loop

```shell
Event → prepare → ┌─ Compliance ─┐
                   ├─ Security   ─┤ → Moderator → Action Items → RM Queue → RM Decides
                   └─ Engineering ┘
```

1. **Event ingestion** — A business event (wire transfer, security alert, velocity trigger) arrives via the `/api/analyze` endpoint
2. **Prepare** — Context preparation stub (future: client memory lookup, RAG retrieval)
3. **Fan-out** — Three domain agents run in parallel via LangGraph
4. **Fan-in** — The moderator receives all three analyses
5. **Synthesis** — The moderator produces consensus, dissent, risk assessment, and action items
6. **RM queue** — Action items are routed to the Relationship Manager for a human decision

---

## Key components

### Backend (FastAPI)

The Python backend handles API routing, agent orchestration, and LLM calls:

- **FastAPI app** (`backend/app/main.py`) — CORS, health check, router registration
- **Analyze endpoints** (`backend/app/api/conversations.py`) — Sync and SSE streaming (stateless)
- **Queue endpoints** (`backend/app/api/queue.py`) — Submit scenarios by name, auto-persist results
- **History endpoints** (`backend/app/api/history.py`) — List, get, and clear persisted conversations
- **LangGraph orchestrator** (`backend/app/agents/orchestrator.py`) — Graph topology
- **Agent nodes** (`backend/app/agents/nodes/`) — Compliance, Security, Engineering, Moderator
- **Prompt templates** (`backend/app/agents/prompts/`) — Version-controlled markdown
- **Conversation store** (`backend/app/services/store.py`) — In-memory persistence for demo use

### Frontend (React + TypeScript)

The frontend provides the RM console interface:

- **Conversation view** — Agent analyses displayed in real-time
- **Action queue** — Sorted by risk severity
- **Client memory panel** — Per-client context and history

{% callout title="Frontend status" %}
The frontend UI is fully styled with Tailwind CSS and uses mock data. API integration via React Query is not yet wired up.
{% /callout %}

### Infrastructure

| Service | Technology | Purpose |
|---------|-----------|---------|
| App server | nginx + uvicorn + supervisord | Reverse proxy + ASGI server |
| Database | PostgreSQL + pgvector | Relational data, JSONB, vector search |
| Cache | Redis | Pub/sub, task queue, caching |

---

## Data flow

### Synchronous (`POST /api/analyze`)

```shell
Client → FastAPI → graph.ainvoke() → [3 agents parallel] → moderator → JSON response
```

### Streaming (`POST /api/analyze/stream`)

```shell
Client → FastAPI → graph.astream() → SSE events:
  1. start
  2. agent_complete (×3, as each finishes)
  3. moderator_complete
  4. done
```

---

## What agents never do

Agents are advisory only. They never:

- Execute transactions or modify account state
- Send external communications
- File regulatory reports
- Override RM decisions

Every action requires explicit human approval through the RM queue.
