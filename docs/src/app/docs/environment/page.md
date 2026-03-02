---
title: Environment variables
---

All SwarmOps configuration is driven by environment variables. Application settings use the `SWARM_` prefix; AWS credentials follow standard conventions. {% .lead %}

---

## Application settings

All prefixed with `SWARM_` and managed by Pydantic Settings.

| Variable | Default | Description |
|----------|---------|-------------|
| `SWARM_BEDROCK_REGION` | `us-east-1` | AWS region for Bedrock API calls |
| `SWARM_BEDROCK_MODEL_ID` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Full Bedrock model identifier |
| `SWARM_LLM_TEMPERATURE` | `0.3` | LLM sampling temperature (0.0 - 1.0) |
| `SWARM_LLM_MAX_TOKENS` | `2048` | Maximum tokens per LLM response |
| `SWARM_CORS_ORIGINS` | `["http://localhost:5173", "http://localhost:3000"]` | Allowed CORS origins (JSON array) |

---

## AWS credentials

SwarmOps needs AWS credentials with Bedrock access. Supported methods:

### Environment variables

```shell
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...     # If using temporary credentials
export AWS_DEFAULT_REGION=us-east-1
```

### AWS profile

```shell
export AWS_PROFILE=my-profile
```

### Docker volume mount

The Docker Compose file mounts `~/.aws` as read-only:

```yaml
volumes:
  - ${HOME}/.aws:/root/.aws:ro
```

---

## Docker Compose environment

The `docker-compose.yml` passes these variables to the app container:

```yaml
environment:
  - SWARM_BEDROCK_REGION=${AWS_REGION:-us-east-1}
  - SWARM_BEDROCK_MODEL_ID=${SWARM_BEDROCK_MODEL_ID:-us.anthropic.claude-sonnet-4-20250514-v1:0}
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_SESSION_TOKEN
  - AWS_PROFILE
  - AWS_DEFAULT_REGION=${AWS_REGION:-us-east-1}
```

Variables without values (like `AWS_ACCESS_KEY_ID`) are passed through from the host environment.

---

## Database

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `swarmops` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `swarmops` | PostgreSQL password |
| `POSTGRES_DB` | `swarmops` | Database name |

These are set in the `postgres` service in `docker-compose.yml`.

---

## Model switching examples

```shell
# Claude Haiku 4.5 (default, fastest)
SWARM_BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0

# Claude Sonnet (more capable)
SWARM_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
```

{% callout title="Model IDs" %}
Use the full model identifier from your AWS Bedrock console, including the region prefix (`us.`) and version suffix.
{% /callout %}
