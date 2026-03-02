---
title: Docker setup
---

SwarmOps runs as a multi-container application with Docker Compose. The main app container uses a multi-stage build with nginx, uvicorn, and supervisord. {% .lead %}

---

## Docker Compose

**File:** `docker-compose.yml`

```yaml
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - SWARM_BEDROCK_REGION=${AWS_REGION:-us-east-1}
      - SWARM_BEDROCK_MODEL_ID=${SWARM_BEDROCK_MODEL_ID:-us.anthropic.claude-sonnet-4-20250514-v1:0}
      - AWS_ACCESS_KEY_ID
      - AWS_SECRET_ACCESS_KEY
      - AWS_SESSION_TOKEN
      - AWS_PROFILE
      - AWS_DEFAULT_REGION=${AWS_REGION:-us-east-1}
    volumes:
      - ${HOME}/.aws:/root/.aws:ro
    depends_on:
      - postgres
      - redis

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: swarmops
      POSTGRES_PASSWORD: swarmops
      POSTGRES_DB: swarmops
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

---

## Dockerfile (multi-stage)

**File:** `Dockerfile`

### Stage 1: Frontend build

Uses Red Hat UBI9 with Node.js 20 to build the React frontend:

```shell
FROM registry.access.redhat.com/ubi9/ubi:latest AS frontend-build

RUN dnf module enable -y nodejs:20 && \
    dnf install -y nodejs npm && \
    dnf clean all

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build
```

### Stage 2: Runtime

Uses UBI9-minimal with Python 3.11, nginx, and supervisord:

```shell
FROM registry.access.redhat.com/ubi9/ubi-minimal:latest

RUN microdnf install -y python3.11 python3.11-pip nginx && \
    microdnf clean all && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    pip3.11 install --no-cache-dir supervisor

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/app/ app/

COPY --from=frontend-build /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisord.conf

EXPOSE 3000
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
```

---

## nginx configuration

**File:** `nginx.conf`

nginx serves as the reverse proxy on port 3000:

```shell
server {
    listen 3000;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }
}
```

| Route | Target | Notes |
|-------|--------|-------|
| `/` | Frontend static files | SPA fallback to `index.html` |
| `/health` | uvicorn (port 8000) | Health check endpoint |
| `/api/` | uvicorn (port 8000) | SSE-aware (no buffering) |

---

## supervisord

**File:** `supervisord.conf`

Manages both nginx and uvicorn as child processes:

```shell
[supervisord]
nodaemon=true

[program:uvicorn]
command=uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
directory=/app/backend
autorestart=true

[program:nginx]
command=nginx -g "daemon off;"
autorestart=true
```

Both processes log to stdout/stderr and auto-restart on failure.

---

## Port mapping

| Service | Port | Description |
|---------|------|-------------|
| App (Docker) | 3000 | nginx: frontend + API proxy |
| PostgreSQL | 5432 | `swarmops/swarmops` |
| Redis | 6379 | Cache and pub/sub |
