---
title: Development guide
---

Run SwarmOps locally without Docker for faster iteration. This guide covers backend, frontend, and full-stack development workflows. {% .lead %}

---

## Backend development

### Setup

```shell
cd backend
uv sync          # Install Python dependencies
```

### Run the dev server

```shell
uv run uvicorn app.main:app --reload
```

The backend runs on `http://localhost:8000` with auto-reload on file changes. Use the [event queue](/docs/event-queue) to quickly submit pre-built scenarios.

### Lint and format

```shell
ruff check . && ruff format .
```

---

## Frontend development

### Setup

```shell
cd frontend
npm install
```

### Run the dev server

```shell
npm run dev
```

The Vite dev server runs on `http://localhost:5173` with HMR.

### Build for production

```shell
npm run build    # Output in dist/
```

---

## Full-stack with Docker

```shell
docker compose up --build -d     # Build and start all services
docker compose logs -f app       # Follow app logs
docker compose down              # Stop everything
docker compose down -v           # Stop + remove data volumes
```

---

## Project structure

```shell
swarmops/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── core/config.py       # Settings (SWARM_ env prefix)
│   │   ├── schemas/events.py    # API request/response models
│   │   ├── api/
│   │   │   ├── conversations.py # Analyze endpoints
│   │   │   └── queue.py         # Queue endpoints (scenario shortcuts)
│   │   └── agents/
│   │       ├── orchestrator.py  # LangGraph StateGraph
│   │       ├── state.py         # SwarmState TypedDict
│   │       ├── schemas.py       # Agent/Moderator output models
│   │       ├── llm.py           # LLM — Bedrock (live) or MockLLM (mock)
│   │       ├── mock_responses.py # Pre-built responses (4 scenarios)
│   │       ├── scenarios.py     # Pre-built AnalyzeRequest objects
│   │       ├── nodes/           # Agent implementations
│   │       └── prompts/         # Markdown prompt templates
│   └── tests/
├── frontend/
│   └── src/
│       ├── types/index.ts       # TypeScript interfaces
│       ├── data/mockData.ts     # Mock conversations
│       ├── components/          # React components
│       └── App.tsx              # Main app
├── docs/                        # This documentation site
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
└── supervisord.conf
```

---

## Ports

| Service | Port | Notes |
|---------|------|-------|
| App (Docker) | 3000 | nginx reverse proxy |
| Backend (local) | 8000 | Direct uvicorn |
| Frontend (local) | 5173 | Vite dev server |
| Docs (local) | 3001 | Next.js dev server |
| PostgreSQL | 5432 | `swarmops/swarmops` |
| Redis | 6379 | |

---

## Build roadmap

The project is built incrementally:

1. ~~FastAPI skeleton + Postgres models~~ (scaffold done, DB models pending)
2. Basic conversation CRUD + single agent call
3. ~~LangGraph orchestrator with parallel agents~~ **DONE**
4. ~~SSE streaming~~ **DONE**
4.5. ~~Mock event queue~~ **DONE** — mock mode for local dev without Bedrock
5. Action items + RM queue
6. Client memory (read/write/approve)
7. ARQ background tasks (knowledge extraction, archival)
8. Frontend API integration (React Query, SSE client)
9. Auth + multi-tenancy
10. Infrastructure + deployment

---

## Adding a new agent

To add a fourth domain agent:

1. Create a prompt template in `backend/app/agents/prompts/newagent.md`
2. Create the agent node in `backend/app/agents/nodes/newagent.py` (follow the existing pattern)
3. Add the node and edges to `backend/app/agents/orchestrator.py`:
   ```python
   builder.add_node("newagent", newagent_func)
   builder.add_edge("prepare", "newagent")
   builder.add_edge("newagent", "moderator")
   ```
4. Add the agent name mapping in `backend/app/api/conversations.py`
5. Update the moderator prompt to expect four agents instead of three
6. Add tests in `backend/tests/test_orchestrator.py`
