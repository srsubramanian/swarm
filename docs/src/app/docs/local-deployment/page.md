---
title: Local deployment
---

A complete walkthrough for deploying the entire SwarmOps stack on your local machine — backend, frontend, docs, database, and cache — with and without Docker. {% .lead %}

---

## Option 1: Docker Compose (recommended)

The fastest way to get everything running. One command starts all five services.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose plugin)
- AWS credentials with Bedrock access (see [Environment variables](/docs/environment))

### Start all services

```shell
cd swarmops
docker compose up --build -d
```

This builds and starts:

| Service | URL | Description |
|---------|-----|-------------|
| **app** | [http://localhost:3000](http://localhost:3000) | Main app — nginx serves frontend at `/`, proxies API at `/api/` |
| **docs** | [http://localhost:3001](http://localhost:3001) | Documentation site (this site) |
| **postgres** | localhost:5432 | PostgreSQL with pgvector, credentials: `swarmops/swarmops` |
| **redis** | localhost:6379 | Redis for cache and pub/sub |

### Verify everything is healthy

```shell
curl http://localhost:3000/health
```

Expected response:

```json
{"status": "ok"}
```

Check all containers are running:

```shell
docker compose ps
```

You should see four services with status `Up`:

```shell
NAME              STATUS
swarm-app-1       Up
swarm-docs-1      Up
swarm-postgres-1  Up
swarm-redis-1     Up
```

### View logs

```shell
docker compose logs -f          # All services
docker compose logs -f app      # Main app only
docker compose logs -f docs     # Docs site only
```

### Send a test event

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
      "destination_bank": "Bank of Cyprus"
    },
    "client_memory": "Known client since 2019. Regular EU transfers."
  }'
```

You should receive a JSON response with three agent analyses and a moderator synthesis.

### Switch the LLM model

```shell
SWARM_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0 docker compose up -d
```

### Stop everything

```shell
docker compose down          # Stop containers, keep data
docker compose down -v       # Stop containers and delete volumes
```

---

## Option 2: Run each service locally (no Docker)

For development with faster reload cycles. You run each service in a separate terminal.

### Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- PostgreSQL 16 with pgvector extension (or use Docker just for Postgres/Redis)
- Redis 7+
- AWS credentials configured (`~/.aws/credentials` or env vars)

### Step 1: Start infrastructure

If you don't want to install Postgres and Redis natively, start just those two with Docker:

```shell
docker compose up -d postgres redis
```

### Step 2: Start the backend

```shell
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

The API is now running at [http://localhost:8000](http://localhost:8000).

Verify:

```shell
curl http://localhost:8000/health
```

### Step 3: Start the frontend

In a new terminal:

```shell
cd frontend
npm install
npm run dev
```

The frontend is now running at [http://localhost:5173](http://localhost:5173).

{% callout title="Frontend uses mock data" %}
The frontend currently uses mock data and is not yet wired to the backend API. You'll see the UI scaffold with sample conversations.
{% /callout %}

### Step 4: Start the docs site

In a new terminal:

```shell
cd docs
npm install
npm run dev
```

The documentation site is now running at [http://localhost:3001](http://localhost:3001).

### Port summary (local mode)

| Service | Port | Command |
|---------|------|---------|
| Backend | 8000 | `uv run uvicorn app.main:app --reload` |
| Frontend | 5173 | `npm run dev` |
| Docs | 3001 | `npm run dev` |
| PostgreSQL | 5432 | Docker or native install |
| Redis | 6379 | Docker or native install |

---

## Option 3: Hybrid (Docker infra + local app)

A common development pattern — run Postgres and Redis in Docker, but run the app and docs locally for fast iteration.

```shell
docker compose up -d postgres redis
```

Then start the backend, frontend, and docs locally as described in Option 2.

{% callout title="CORS origins" %}
The default CORS configuration allows both `http://localhost:5173` (Vite dev server) and `http://localhost:3000` (Docker nginx). If you use a different port, update the `SWARM_CORS_ORIGINS` environment variable. See [Configuration](/docs/configuration).
{% /callout %}

---

## AWS credentials setup

SwarmOps needs AWS credentials to call Bedrock. Choose one method:

### Method 1: AWS profile (simplest)

```shell
aws configure --profile swarmops
export AWS_PROFILE=swarmops
```

The Docker Compose file mounts `~/.aws` as a read-only volume automatically.

### Method 2: Environment variables

```shell
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
```

### Method 3: SSO / temporary credentials

```shell
aws sso login --profile my-sso-profile
export AWS_PROFILE=my-sso-profile
```

{% callout type="warning" title="Bedrock access required" %}
Your AWS credentials must have access to the Amazon Bedrock `InvokeModel` API for the configured model. By default this is Claude Haiku 4.5. If you get `AccessDeniedException`, check that your IAM policy includes `bedrock:InvokeModel` and that the model is enabled in your Bedrock console for the configured region.
{% /callout %}

---

## Troubleshooting

### Backend won't start

**`ModuleNotFoundError`** — Run `uv sync` in the `backend/` directory to install dependencies.

**`ThrottlingException` from Bedrock** — The three parallel agents can trigger Bedrock rate limits. The LLM client retries up to 8 times with adaptive backoff. If it persists, switch to a model with higher throughput or reduce parallel load.

**Port 8000 already in use** — Kill the existing process or use a different port:

```shell
uv run uvicorn app.main:app --reload --port 8001
```

### Frontend won't start

**Port 5173 already in use** — Vite will auto-increment to the next available port (5174, 5175, etc.).

**`npm install` fails** — Ensure Node.js 20+ is installed: `node --version`.

### Docker build fails

**Stage 1 (frontend)** — Ensure `frontend/package-lock.json` exists. Run `cd frontend && npm install` first if needed.

**Stage 2 (backend)** — Ensure `backend/uv.lock` exists. Run `cd backend && uv lock` first if needed.

### Cannot connect to Postgres/Redis

If running infrastructure in Docker and the app locally, ensure the containers are running:

```shell
docker compose ps postgres redis
```

Check that ports 5432 and 6379 are not blocked by another process:

```shell
lsof -i :5432
lsof -i :6379
```

### Docs site build fails

The docs site requires the `--webpack` flag (already set in `package.json` scripts). If building manually:

```shell
cd docs
npx next build --webpack
```
