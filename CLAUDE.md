# SwarmOps

Multi-agent AI commentary system for fintech operations. Business events (wire transfers, security alerts, compliance reviews) trigger parallel analysis by three domain-specific AI agents. A moderator synthesizes their output into actionable recommendations routed to a human Relationship Manager (RM) who makes all final decisions — agents never act autonomously.

**Core loop:** Event → 3 parallel agents (Compliance, Security, Engineering) → Moderator synthesis → Action item to RM queue → RM decides (approve/reject/escalate/override)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11 |
| Agent Orchestration | LangGraph (StateGraph fan-out/fan-in) |
| LLM | AWS Bedrock (Claude Haiku 4.5 default, configurable via `SWARM_BEDROCK_MODEL_ID`) |
| Database | PostgreSQL + pgvector (relational, JSONB, vectors, full-text search) |
| Cache + Pub/Sub | Redis |
| Background Tasks | ARQ (async Redis-based task queue + cron) |
| Real-time | Server-Sent Events (SSE) |
| Frontend | React + TypeScript + TailwindCSS, React Query |
| Auth | OAuth2/OIDC, JWT with `tenant_id` claim (multi-tenant) |
| Migrations | Alembic |
| Infra | AWS — ECS Fargate, RDS, ElastiCache, S3 |

## Project Structure

```
swarmops/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint + CORS + router registration
│   │   ├── core/
│   │   │   └── config.py        # Settings(BaseSettings) — Bedrock region/model, CORS origins (env prefix: SWARM_)
│   │   ├── schemas/
│   │   │   └── events.py        # AnalyzeRequest/Response, AgentAnalysisResponse, ModeratorSynthesisResponse
│   │   ├── api/
│   │   │   ├── conversations.py # POST /api/analyze (sync) + POST /api/analyze/stream (SSE)
│   │   │   └── queue.py         # POST /api/queue (sync/stream) + GET /api/queue/scenarios
│   │   ├── agents/
│   │   │   ├── orchestrator.py  # StateGraph: fan-out 3 agents → moderator (compiled graph singleton)
│   │   │   ├── state.py         # SwarmState(TypedDict) with Annotated[list, operator.add] reducer
│   │   │   ├── schemas.py       # AgentAnalysis, ModeratorSynthesis, ActionItem (structured LLM output)
│   │   │   ├── llm.py           # Cached ChatBedrockConverse with adaptive retry
│   │   │   ├── scenarios.py     # 4 pre-built AnalyzeRequest objects for event queue
│   │   │   ├── nodes/
│   │   │   │   ├── prepare.py       # Context preparation stub (extension point for memory/RAG)
│   │   │   │   ├── compliance.py    # AML/KYC/sanctions analysis
│   │   │   │   ├── security.py      # Threat/fraud/auth analysis
│   │   │   │   ├── engineering.py   # API/SDK/metadata analysis
│   │   │   │   └── moderator.py     # Synthesis of all agent analyses
│   │   │   └── prompts/             # Markdown prompt templates (version controlled)
│   │   │       ├── compliance.md
│   │   │       ├── security.md
│   │   │       ├── engineering.md
│   │   │       └── moderator.md
│   │   ├── models/              # (future) SQLAlchemy models
│   │   ├── services/            # (future) Business logic layer
│   │   ├── tasks/               # (future) ARQ background tasks
│   │   └── ws/                  # (future) SSE streaming endpoints
│   ├── tests/
│   │   ├── test_orchestrator.py # Graph topology + full run with mocked LLM + API endpoint tests
│   │   └── test_queue.py        # Scenario registry + queue endpoint tests (11 tests)
│   └── requests.http            # HTTP client file for manual API testing
├── frontend/
│   └── src/
│       ├── types/index.ts       # TypeScript interfaces (AgentInfo, Message, ModeratorSummaryData, etc.)
│       ├── data/mockData.ts     # Mock conversations for UI development
│       ├── components/          # conversation/, sidebar/, memory/, shared/ — fully styled with Tailwind
│       └── App.tsx              # Main app (uses mock data, not yet wired to backend)
├── docker-compose.yml           # Local dev: app (nginx+uvicorn) + postgres(pgvector) + redis
├── Dockerfile                   # Multi-stage: frontend build → nginx + uvicorn + supervisord
├── nginx.conf                   # Reverse proxy: / → frontend, /api/ → backend, SSE-aware
├── supervisord.conf             # Process manager for nginx + uvicorn
├── infra/                       # (future) Terraform (ECS, RDS, ElastiCache, S3, ALB)
└── scripts/                     # (future) seed_data, create_partitions, migrations
```

## Development Commands

```bash
# Docker (full stack — frontend + backend + postgres + redis)
docker compose up --build -d       # build and start all services
docker compose logs -f app         # follow app logs
docker compose down                # stop everything

# Switch LLM model via env var
SWARM_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0 docker compose up -d

# Backend (local, without Docker)
cd backend
uv run uvicorn app.main:app --reload      # dev server on :8000
uv run pytest tests/ -v                    # run tests
uv run pytest tests/test_orchestrator.py   # single test file
ruff check . && ruff format .              # lint + format

# Frontend (local, without Docker)
cd frontend
npm run dev                        # dev server on :5173
npm test                           # tests
npm run build                      # production build
```

### Ports

| Service | Port | Notes |
|---------|------|-------|
| App (Docker) | 3000 | nginx: `/` → frontend, `/api/` → backend, `/health` → backend |
| Backend (local) | 8000 | Direct uvicorn |
| Frontend (local) | 5173 | Vite dev server |
| PostgreSQL | 5432 | `swarmops/swarmops` |
| Redis | 6379 | |

## Architecture — Key Concepts

### Agent Orchestration (LangGraph)

The orchestrator is a `StateGraph` with fan-out/fan-in topology:

1. **Fan-out**: Three agent nodes run in parallel — Compliance (AML/KYC/regulatory), Security (threats/vulnerabilities), Engineering (technical feasibility)
2. **Cross-reference**: Agents can reference each other's analysis — Security pushes back on Engineering, Compliance cites regulations, they converge or disagree
3. **Moderator**: Synthesizes all agent outputs into a structured summary — consensus, dissent, risk level, next steps
4. **Side-effects**: Moderator output triggers action item creation and memory update proposals

Shared state is a `TypedDict` passed through the graph. Prompt templates live in `agents/prompts/` as version-controlled markdown files.

### Client Memory

Each client has a dedicated memory file (markdown stored in Postgres). Agents read this memory before analysis for context (e.g., "this client had a similar velocity spike last month — it was legitimate payroll").

- Memory accumulates learned behaviors over time
- All memory edits require RM approval (human-in-the-loop)
- A nightly ARQ compaction job generalizes specifics into patterns

### Conversation Lifecycle

`Live` → `Concluded` → `Indexed` (knowledge extracted, embedded for RAG) → `Archived` (messages to S3, metadata stays in Postgres) → `Purged` (per retention policy)

### RM Console

RMs see an **action queue** sorted by risk severity, not real-time agent conversations. Each action item is expandable:

- Agent analysis summary
- Client memory context
- Available actions with two-step confirmation
- Overrides require written justification → creates audit trail entry

## Build Approach

The project is scaffolded incrementally. Each step is self-contained:

1. ~~FastAPI skeleton + Postgres models + Alembic migrations~~ (scaffold done, DB models pending)
2. Basic conversation CRUD + single agent call (no fan-out yet)
3. **LangGraph orchestrator with parallel agents** — DONE
4. **SSE streaming** — DONE (bundled with step 3)
4.5. **Event queue with pre-built scenarios** — DONE (submit scenarios by name via `/api/queue`)
5. Action items + RM queue
6. Client memory (read/write/approve)
7. ARQ background tasks (knowledge extraction, archival, compaction)
8. Frontend pages one at a time (UI scaffold done, API wiring pending)
9. Auth + multi-tenancy
10. Infrastructure + deployment

### What's Built (Steps 1, 3, 4, 4.5)

- **FastAPI app** with CORS, health check, analyze endpoints, and queue endpoints
- **LangGraph orchestrator** — `START → prepare → [compliance | security | engineering] → moderator → END`
- **3 domain agents** running in parallel via LangGraph fan-out, each with structured output (`AgentAnalysis`)
- **Moderator node** synthesizing into `ModeratorSynthesis` with action items
- **SSE streaming** via `graph.astream(stream_mode="updates")` — emits `start`, `agent_complete` (×3), `moderator_complete`, `done`
- **Event queue** — 4 pre-built scenarios (wire_transfer, velocity_alert, security_alert, cash_deposit) with distinct risk profiles; queue endpoints (`/api/queue`) accept scenario names instead of full JSON payloads and delegate to the real LLM pipeline
- **Adaptive retry** on Bedrock calls (handles throttling from parallel agent calls)
- **Pydantic validators** to coerce LLM output quirks (bullet strings → lists)
- **Docker setup** — multi-stage build, nginx reverse proxy with SSE support, supervisord
- **Frontend UI** — fully styled conversation components (using mock data, not yet wired to API)
- **Tests** — 17 passing (topology, mocked LLM full run, API endpoint, scenarios, queue endpoints)

### What's NOT Built Yet

- Database models / Alembic migrations
- Conversation CRUD / persistence
- Action item queue with RM approve/reject/escalate
- Client memory read/write/approve
- ARQ background tasks
- Frontend API integration (React Query hooks, SSE client)
- Auth / multi-tenancy
- Infrastructure / deployment

**Ask which step to work on.** I'll scope it tightly and we'll build just that piece.
