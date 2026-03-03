---
title: System overview
---

SwarmOps follows a simple pipeline: business events enter, three AI agents analyze them in parallel, a moderator synthesizes the results, and a human Relationship Manager makes the final call. {% .lead %}

---

## The core loop

```shell
Event → prepare → ┌─ Compliance ─┐
                   ├─ Security   ─┤ → Moderator → await_decision (pause) → RM Decides → post_decision
                   └─ Engineering ┘
```

1. **Event ingestion** — A business event (wire transfer, security alert, velocity trigger) arrives via `/api/queue` or `/api/events/webhook`
2. **Prepare** — Client memory lookup from `ClientMemoryStore`, injected into agent context
3. **Triage** *(event graph only)* — LLM classifies the event as `respond` / `notify` / `ignore`
4. **Fan-out** — Three domain agents run in parallel via LangGraph
5. **Fan-in** — The moderator receives all three analyses
6. **Synthesis** — The moderator produces consensus, dissent, risk assessment, and action items
7. **Await decision** — Graph pauses via `interrupt()` — conversation saved with status `awaiting_decision`
8. **RM decides** — RM reviews and submits a decision (approve/reject/escalate) via the Decisions API
9. **Post-decision** — Graph resumes, records the outcome, proposes client memory updates

---

## Key components

### Backend (FastAPI)

The Python backend handles API routing, agent orchestration, and LLM calls:

- **FastAPI app** (`backend/app/main.py`) — CORS, health check, router registration, lifespan handler
- **Analyze endpoints** (`backend/app/api/conversations.py`) — Sync and SSE streaming (stateless)
- **Queue endpoints** (`backend/app/api/queue.py`) — Submit scenarios by name, auto-persist results with checkpointing
- **Decision endpoint** (`backend/app/api/decisions.py`) — RM submits decisions, resumes paused graphs
- **Memory endpoints** (`backend/app/api/memory.py`) — Per-client memory read/propose/approve/reject
- **Events endpoints** (`backend/app/api/events.py`) — Webhook ingestion, event simulator start/stop
- **History endpoints** (`backend/app/api/history.py`) — List, get, and clear persisted conversations
- **LangGraph orchestrator** (`backend/app/agents/orchestrator.py`) — Three graph variants with checkpointing
- **Agent nodes** (`backend/app/agents/nodes/`) — Compliance, Security, Engineering, Moderator, Triage, Await Decision, Post Decision, Notify
- **Prompt templates** (`backend/app/agents/prompts/`) — Version-controlled markdown (6 prompts)
- **Memory store** (`backend/app/services/memory_store.py`) — Per-client memory with pending update approval
- **Conversation store** (`backend/app/services/store.py`) — In-memory persistence + thread mapping

### Frontend (React + TypeScript)

The frontend provides the RM console interface, wired to the backend via React Query:

- **Conversation view** — Agent analyses fetched from API with auto-polling
- **Action queue** — Sorted by risk severity, status badges (live/awaiting decision/concluded)
- **Decision UI** — Action buttons with two-step confirmation, justification for danger actions, loading state during mutation
- **Scenario panel** — Submit pre-built scenarios from the sidebar
- **Client memory panel** — Per-client context and history
- **React Query hooks** — `useConversations`, `useDecision`, `useScenarios`, `useSSE`

### Infrastructure

| Service | Technology | Purpose |
|---------|-----------|---------|
| App server | nginx + uvicorn + supervisord | Reverse proxy + ASGI server |
| Database | PostgreSQL + pgvector | Relational data, JSONB, vector search |
| Cache | Redis | Pub/sub, task queue, caching |

---

## Data flow

### Stateless (`POST /api/analyze`)

```shell
Client → FastAPI → stateless_graph.ainvoke() → [3 agents parallel] → moderator → JSON response
```

### Queue with decision pause (`POST /api/queue`)

```shell
Client → FastAPI → graph.ainvoke() → [3 agents parallel] → moderator → await_decision (interrupt)
                                                                              ↓
                                                              POST /api/decisions/{id}
                                                                              ↓
                                                              graph.ainvoke(Command(resume=)) → post_decision → JSON response
```

### Event webhook with triage (`POST /api/events/webhook`)

```shell
Client → FastAPI → event_graph.ainvoke() → triage → respond/notify/ignore → ...
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
