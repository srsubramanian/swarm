# SwarmOps

Multi-agent AI commentary system for fintech operations. Business events (wire transfers, security alerts, compliance reviews) trigger parallel analysis by three domain-specific AI agents. A moderator synthesizes their output into actionable recommendations routed to a human Relationship Manager (RM) who makes all final decisions — agents never act autonomously.

**Core loop:** Event → 3 parallel agents (Compliance, Security, Engineering) → Moderator synthesis → Action item to RM queue → RM decides (approve/reject/escalate/override)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.12 |
| Agent Orchestration | LangGraph (StateGraph fan-out/fan-in) |
| LLM | AWS Bedrock (Claude Sonnet) |
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
│   └── app/
│       ├── main.py              # FastAPI entrypoint
│       ├── core/                # config, database, auth, redis, security
│       ├── models/              # SQLAlchemy: conversation, message, client, action_item, memory, audit_log, knowledge
│       ├── schemas/             # Pydantic request/response DTOs
│       ├── api/                 # REST endpoints: conversations, action_items, clients, memory, auth, admin
│       ├── services/            # Business logic layer
│       ├── agents/
│       │   ├── orchestrator.py  # StateGraph: fan-out 3 agents → moderator → memory + action items
│       │   ├── state.py         # Shared TypedDict state
│       │   ├── nodes/           # compliance.py, security.py, engineering.py, moderator.py, memory_update.py
│       │   └── prompts/         # Markdown prompt templates (version controlled)
│       ├── tasks/               # ARQ tasks: knowledge_extraction, memory_updates, archive, audit, notifications
│       ├── worker.py            # ARQ worker settings + cron schedule
│       └── ws/                  # SSE streaming endpoints
├── frontend/
│   └── src/
│       ├── api/                 # React Query hooks + SSE client
│       ├── pages/               # Dashboard, Queue, Conversation, ConversationHistory, ClientDetail
│       ├── components/          # conversation/, queue/, memory/, shared/
│       └── hooks/               # useSSE, useInfiniteScroll, useRoleGuard
├── infra/                       # Terraform (ECS, RDS, ElastiCache, S3, ALB)
├── scripts/                     # seed_data, create_partitions, migrations
└── docker-compose.yml           # Local dev: api + worker + postgres(pgvector) + redis
```

## Development Commands

```bash
# Local environment
docker-compose up                  # api + worker + postgres + redis

# Backend
cd backend
uvicorn app.main:app --reload      # dev server
alembic upgrade head               # run migrations
alembic revision --autogenerate -m "description"  # create migration
pytest                             # all tests
pytest tests/test_foo.py::test_bar # single test
ruff check . && ruff format .      # lint + format

# Frontend
cd frontend
npm run dev                        # dev server
npm test                           # tests
npm run build                      # production build

# Worker
cd backend
arq app.worker.WorkerSettings      # start ARQ worker
```

> Commands above are the intended conventions. Adjust as the project is scaffolded.

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

1. FastAPI skeleton + Postgres models + Alembic migrations
2. Basic conversation CRUD + single agent call (no fan-out yet)
3. LangGraph orchestrator with parallel agents
4. SSE streaming
5. Action items + RM queue
6. Client memory (read/write/approve)
7. ARQ background tasks (knowledge extraction, archival, compaction)
8. Frontend pages one at a time
9. Auth + multi-tenancy
10. Infrastructure + deployment

**Ask which step to work on.** I'll scope it tightly and we'll build just that piece.
