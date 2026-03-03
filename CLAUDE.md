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
│   │   │   ├── events.py        # AnalyzeRequest/Response, AgentAnalysisResponse, ModeratorSynthesisResponse
│   │   │   └── conversations.py # ConversationRecord + nested models (camelCase aliases matching frontend types)
│   │   ├── api/
│   │   │   ├── conversations.py # POST /api/analyze (sync) + POST /api/analyze/stream (SSE)
│   │   │   ├── queue.py         # POST /api/queue (sync/stream) + GET /api/queue/scenarios — persists to store
│   │   │   ├── history.py       # GET/DELETE /api/conversations, GET /api/conversations/{id}
│   │   │   ├── decisions.py     # POST /api/decisions/{id} — RM submits decision, resumes interrupted graph
│   │   │   ├── memory.py        # GET /api/memory/{client}, GET/POST /api/memory/pending — client memory CRUD
│   │   │   └── events.py        # POST /api/events/webhook, POST /api/events/simulate/start|stop
│   │   ├── agents/
│   │   │   ├── orchestrator.py  # StateGraph: 3 graph variants (stateless, stateful+interrupt, event+triage)
│   │   │   ├── state.py         # SwarmState(TypedDict) with Annotated[list, operator.add] reducer
│   │   │   ├── schemas.py       # AgentAnalysis, ModeratorSynthesis, ActionItem (structured LLM output)
│   │   │   ├── llm.py           # Cached ChatBedrockConverse with adaptive retry
│   │   │   ├── tool_loop.py     # Shared run_agent_with_tools() — two-phase helper (tool loop + structured extraction)
│   │   │   ├── scenarios.py     # 4 pre-built AnalyzeRequest objects for event queue
│   │   │   ├── tools/               # Domain-specific mock tools for deep agent analysis
│   │   │   │   ├── __init__.py          # TOOLS_BY_DOMAIN registry
│   │   │   │   ├── compliance_tools.py  # search_sanctions_list, get_client_transaction_history, check_regulatory_thresholds
│   │   │   │   ├── security_tools.py    # lookup_ip_reputation, check_geo_velocity, get_device_fingerprint_history
│   │   │   │   └── engineering_tools.py # check_sdk_version_status, get_api_rate_limit_status, validate_transaction_metadata
│   │   │   ├── nodes/
│   │   │   │   ├── prepare.py       # Fetches client memory from memory store before analysis
│   │   │   │   ├── compliance.py    # AML/KYC/sanctions analysis (deep agent with tool use)
│   │   │   │   ├── security.py      # Threat/fraud/auth analysis (deep agent with tool use)
│   │   │   │   ├── engineering.py   # API/SDK/metadata analysis (deep agent with tool use)
│   │   │   │   ├── moderator.py     # Synthesis of all agent analyses (single structured output call)
│   │   │   │   ├── triage.py        # Triage router — classifies events as respond/notify/ignore
│   │   │   │   ├── notify.py        # Lightweight RM notification for triaged events
│   │   │   │   ├── await_decision.py # interrupt() — pauses graph for RM decision
│   │   │   │   └── post_decision.py # Records decision, proposes memory updates via LLM
│   │   │   └── prompts/             # Markdown prompt templates (version controlled)
│   │   │       ├── compliance.md    # Includes Available Tools section
│   │   │       ├── security.md      # Includes Available Tools section
│   │   │       ├── engineering.md   # Includes Available Tools section
│   │   │       ├── moderator.md
│   │   │       ├── triage.md        # Triage classification prompt
│   │   │       └── memory_update.md # Memory update proposal prompt
│   │   ├── models/              # (future) SQLAlchemy models
│   │   ├── services/
│   │   │   ├── store.py             # InMemoryConversationStore + ThreadStore singletons (dict-backed, demo use)
│   │   │   ├── conversation_builder.py  # build_conversation(req, analyses, synthesis) → ConversationRecord
│   │   │   ├── memory_store.py      # ClientMemoryStore — per-client memory with pending update approval
│   │   │   └── event_source.py      # EventSimulator — generates random events on a timer
│   │   ├── tasks/               # (future) ARQ background tasks
│   │   └── ws/                  # (future) SSE streaming endpoints
│   ├── tests/
│   │   ├── test_orchestrator.py   # Graph topology + full run with mocked LLM + API endpoint tests
│   │   ├── test_queue.py          # Scenario registry + queue endpoint tests
│   │   ├── test_conversations.py  # Store, builder, history endpoint, and camelCase serialization tests
│   │   ├── test_tool_agents.py    # Tool unit tests + tool loop tests + full graph integration with tools
│   │   ├── test_decisions.py      # Decision endpoint + interrupt/resume + graph checkpointing tests
│   │   ├── test_memory.py         # Memory store, prepare node, memory API endpoint tests
│   │   └── test_triage.py         # Triage classification, event graph, webhook, simulator tests
│   └── requests.http            # HTTP client file for manual API testing
├── frontend/
│   └── src/
│       ├── types/index.ts       # TypeScript interfaces (AgentInfo, Message, DecisionPayload, Scenario, etc.)
│       ├── data/mockData.ts     # Mock conversations for UI development (retained for reference)
│       ├── hooks/               # React Query hooks for API integration
│       │   ├── useConversations.ts  # GET /api/conversations with 5s polling
│       │   ├── useConversation.ts   # GET /api/conversations/{id}
│       │   ├── useDecision.ts       # POST /api/decisions/{id} mutation
│       │   ├── useScenarios.ts      # GET /api/queue/scenarios + POST /api/queue mutation
│       │   └── useSSE.ts            # SSE streaming client for /api/queue/stream
│       ├── components/
│       │   ├── ScenarioPanel.tsx     # Scenario selection + submission UI in sidebar
│       │   ├── layout/AppShell.tsx   # Main app — React Query hooks, decision flow
│       │   ├── conversation/         # Header, MessageList, MessageBubble, ModeratorSummary, ActionBar
│       │   ├── sidebar/              # QueueList, QueueItem — wired to conversation status
│       │   ├── memory/               # MemoryDrawer
│       │   └── shared/               # Badge, AgentIcon, FormattedContent
│       └── App.tsx              # QueryClientProvider + AppShell
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

1. **Fan-out**: Three **deep agent** nodes run in parallel — Compliance (AML/KYC/regulatory), Security (threats/vulnerabilities), Engineering (technical feasibility). Each agent has an internal tool-calling loop to gather evidence before forming its assessment.
2. **Tool use**: Each agent has 3 domain-specific tools (9 total). The agent calls tools, receives results, iterates until it has enough evidence, then a final structured-output call extracts the `AgentAnalysis`. The LangGraph topology is unchanged — tool loops are entirely internal to each node.
3. **Cross-reference**: Agents can reference each other's analysis — Security pushes back on Engineering, Compliance cites regulations, they converge or disagree
4. **Moderator**: Synthesizes all agent outputs into a structured summary — consensus, dissent, risk level, next steps (single LLM call, no tool use)
5. **Side-effects**: Moderator output triggers action item creation and memory update proposals

Shared state is a `TypedDict` passed through the graph. Prompt templates live in `agents/prompts/` as version-controlled markdown files. Tool definitions live in `agents/tools/` with a `TOOLS_BY_DOMAIN` registry.

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
4.6. **Conversation history (in-memory)** — DONE (queue submissions auto-persist, history endpoints for list/get/clear)
4.7. **Deep agents with tool use** — DONE (agents call domain-specific tools to gather evidence before forming assessments)
5. **Action items + RM decision queue** — DONE (interrupt/resume with checkpointing, decision API)
6. **Client memory (read/write/approve)** — DONE (memory store, prepare node reads, post_decision proposes updates)
7. **Triage + background event processing** — DONE (triage router, event simulator, webhook endpoint)
8. **Frontend API integration** — DONE (React Query hooks, decision UI, SSE streaming, scenario panel)
9. Auth + multi-tenancy
10. Infrastructure + deployment

### What's Built (Steps 1, 3–8)

- **FastAPI app** with CORS, health check, analyze endpoints, queue endpoints, history endpoints, decision endpoint, memory endpoints, and event endpoints
- **LangGraph orchestrator** — three graph variants:
  - `stateless_graph` — no checkpoint, for `/api/analyze` (runs to END)
  - `graph` — with `InMemorySaver` checkpointer + `interrupt()` for `/api/queue` (pauses at `await_decision`)
  - `event_graph` — with triage + checkpointing for webhook/simulator (conditional routing)
- **Graph topology** (stateful): `START → prepare → [compliance | security | engineering] → moderator → await_decision → post_decision → END`
- **Graph topology** (event): `START → prepare → triage → {respond: [agents] → moderator → await_decision → post_decision → END, notify: notify_rm → END, ignore: END}`
- **3 deep agents** running in parallel via LangGraph fan-out, each with an **internal tool-calling loop** that gathers evidence before producing structured output (`AgentAnalysis`)
  - **Compliance tools**: `search_sanctions_list`, `get_client_transaction_history`, `check_regulatory_thresholds`
  - **Security tools**: `lookup_ip_reputation`, `check_geo_velocity`, `get_device_fingerprint_history`
  - **Engineering tools**: `check_sdk_version_status`, `get_api_rate_limit_status`, `validate_transaction_metadata`
  - Tools return **simulated mock data** keyed on the 4 built-in scenarios — clean interfaces for swapping in real implementations later
  - Shared `run_agent_with_tools()` helper uses a **two-phase approach**: Phase 1 `bind_tools()` for evidence gathering (up to 5 iterations), Phase 2 `with_structured_output()` for structured extraction
- **Moderator node** synthesizing into `ModeratorSynthesis` with action items (single structured output call — no tool use)
- **RM Decision Queue** — `await_decision` node calls `interrupt()` to pause graph; RM submits decision via `POST /api/decisions/{id}`; graph resumes via `Command(resume=)` through `post_decision` node; conversations transition from `awaiting_decision` → `concluded`
- **Client Memory** — `ClientMemoryStore` with per-client memory + pending update approval; `prepare` node reads stored memory; `post_decision` proposes memory updates via LLM; RM approves/rejects via memory endpoints
- **Triage Router** — LLM-based event classification (respond/notify/ignore); `Send()` for conditional fan-out; `event_graph` includes triage before agent fan-out
- **Event Simulator** — `EventSimulator` generates random events on configurable interval; webhook endpoint for external events; simulator start/stop via API
- **SSE streaming** via `graph.astream(stream_mode="updates")` — emits `start`, `agent_complete` (×3), `moderator_complete`, `done`
- **Event queue** — 4 pre-built scenarios (wire_transfer, velocity_alert, security_alert, cash_deposit) with distinct risk profiles; queue endpoints (`/api/queue`) accept scenario names, run the full LLM pipeline, and **persist results** as `ConversationRecord`
- **Conversation history** — In-memory store (`InMemoryConversationStore`) auto-saves queue submissions; history endpoints for listing, retrieving, and clearing; response shape matches frontend `Conversation` type (camelCase JSON via Pydantic aliases); `/api/analyze` endpoints remain stateless
- **Adaptive retry** on Bedrock calls (handles throttling from parallel agent calls)
- **Pydantic validators** to coerce LLM output quirks (bullet strings → lists)
- **Docker setup** — multi-stage build, nginx reverse proxy with SSE support, supervisord
- **Frontend UI** — fully wired to backend via React Query hooks; scenario submission panel; RM decision flow with two-step confirmation + justification for danger actions; SSE streaming client; conversation status badges; 5s polling for new conversations
- **Tests** — 104 passing (topology, mocked LLM full run, API endpoints, scenarios, queue endpoints, store, builder, history endpoints, camelCase serialization, tool unit tests, tool loop, full graph integration, decision flow, interrupt/resume, memory store, prepare node, memory API, triage edge, event graph, webhook, simulator control)

### What's NOT Built Yet

- Database models / Alembic migrations (in-memory stores used for now)
- ARQ background tasks (knowledge extraction, archival, compaction)
- Auth / multi-tenancy
- Infrastructure / deployment

**Ask which step to work on.** I'll scope it tightly and we'll build just that piece.
