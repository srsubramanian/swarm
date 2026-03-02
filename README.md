# SwarmOps

Multi-agent AI commentary system for fintech operations. Business events (wire transfers, security alerts, compliance reviews) trigger parallel analysis by three domain-specific AI agents. A moderator synthesizes their output into actionable recommendations routed to a human Relationship Manager (RM).

**Agents never act autonomously — the RM makes all final decisions.**

## How It Works

```
Event → prepare → ┌─ Compliance Agent ─┐
                   ├─ Security Agent   ─┤ → Moderator → Action Items → RM Queue
                   └─ Engineering Agent ┘
```

1. A business event arrives (e.g., "$2.4M wire transfer to Cyprus")
2. Three domain agents analyze it **in parallel** via LangGraph fan-out
3. A moderator synthesizes their analyses into consensus, dissent, risk level, and action items
4. The RM reviews and decides (approve / reject / escalate / override)

### Agent Domains

| Agent | Focus |
|-------|-------|
| **Compliance** | AML/KYC, sanctions screening, regulatory reporting (SAR/CTR), transaction typologies |
| **Security** | Authentication anomalies, fraud indicators, device/geo/IP analysis, attack patterns |
| **Engineering** | API integrity, SDK versions, metadata validation, rate limiting, system behavior |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- AWS credentials with Bedrock access (Claude models enabled)

### Run

```bash
docker compose up --build -d
```

The app starts on **http://localhost:3000**:

| Path | What |
|------|------|
| `/` | Frontend UI |
| `/api/analyze` | Sync analysis endpoint |
| `/api/analyze/stream` | SSE streaming endpoint |
| `/health` | Health check |

### Switch LLM Model

```bash
# Claude Haiku 4.5 (default — fast, cheap)
docker compose up -d

# Claude Sonnet 4 (better quality, slower)
SWARM_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0 docker compose up -d
```

### Test the API

Use the included `backend/requests.http` file (VS Code REST Client or IntelliJ HTTP Client), or:

```bash
curl -X POST http://localhost:3000/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "event_type": "wire_transfer",
    "title": "$2.4M Wire to Cyprus",
    "client_name": "Meridian Holdings",
    "event_data": {
      "amount": 2400000,
      "currency": "USD",
      "destination_country": "CY",
      "destination_bank": "Bank of Cyprus"
    },
    "client_memory": "Known client since 2019. Regular EU transfers for trade finance."
  }'
```

### Run Tests

```bash
cd backend
uv run pytest tests/ -v
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11 |
| Agent Orchestration | LangGraph (StateGraph fan-out/fan-in) |
| LLM | AWS Bedrock (Claude Haiku 4.5 default, configurable) |
| Real-time | Server-Sent Events (SSE) via sse-starlette |
| Frontend | React 19 + TypeScript + Tailwind CSS 4 |
| Infra | Docker, nginx, supervisord |
| Database | PostgreSQL + pgvector (planned) |
| Cache | Redis (planned) |

## Project Status

### Built

- LangGraph orchestrator with 3 parallel agents + moderator synthesis
- Sync and SSE streaming API endpoints
- Structured LLM output with Pydantic validation
- Adaptive retry for Bedrock throttling
- Docker multi-stage build (frontend + backend + nginx)
- Frontend UI scaffold (conversation view, queue, memory drawer)
- 6 passing tests (topology, mocked LLM, API)

### Planned

- Database models + Alembic migrations
- Conversation CRUD + persistence
- Action item queue with RM decisions
- Client memory (read/write/approve)
- Background tasks (ARQ)
- Frontend API integration
- Auth + multi-tenancy
- AWS deployment (ECS Fargate, RDS, ElastiCache)

## Configuration

All settings use the `SWARM_` env prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `SWARM_BEDROCK_REGION` | `us-east-1` | AWS Bedrock region |
| `SWARM_BEDROCK_MODEL_ID` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Bedrock model ID |
| `SWARM_LLM_TEMPERATURE` | `0.3` | LLM temperature |
| `SWARM_LLM_MAX_TOKENS` | `2048` | Max tokens per LLM call |
| `SWARM_CORS_ORIGINS` | `["http://localhost:5173", "http://localhost:3000"]` | Allowed CORS origins |
