---
title: Configuration
---

All SwarmOps settings are managed through environment variables with the `SWARM_` prefix, powered by Pydantic Settings. {% .lead %}

---

## Settings class

The configuration is defined in `backend/app/core/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = {"env_prefix": "SWARM_"}

    bedrock_region: str = "us-east-1"
    bedrock_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
```

Settings are loaded once via `@lru_cache` and shared across the application.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SWARM_BEDROCK_REGION` | `us-east-1` | AWS region for Bedrock API calls |
| `SWARM_BEDROCK_MODEL_ID` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Bedrock model identifier |
| `SWARM_LLM_TEMPERATURE` | `0.3` | LLM sampling temperature |
| `SWARM_LLM_MAX_TOKENS` | `2048` | Maximum tokens per LLM response |
| `SWARM_CORS_ORIGINS` | `["http://localhost:5173", "http://localhost:3000"]` | Allowed CORS origins |

---

## AWS credentials

SwarmOps requires AWS credentials with Bedrock access. The Docker setup mounts `~/.aws` as a read-only volume. You can also pass credentials directly:

```shell
AWS_ACCESS_KEY_ID=... \
AWS_SECRET_ACCESS_KEY=... \
AWS_SESSION_TOKEN=... \
docker compose up -d
```

Or use an AWS profile:

```shell
AWS_PROFILE=my-profile docker compose up -d
```

---

## Model switching

To switch between Claude models at runtime:

```shell
# Use Claude Sonnet
SWARM_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0 docker compose up -d

# Use Claude Haiku (default)
SWARM_BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0 docker compose up -d
```

{% callout title="Note on model IDs" %}
Bedrock model IDs include a region prefix (e.g., `us.`) and a version suffix. Use the full identifier as shown in your AWS Bedrock console.
{% /callout %}

---

## LLM retry configuration

The LLM client is configured with adaptive retry in `backend/app/agents/llm.py`:

```python
from botocore.config import Config as BotoConfig

BotoConfig(
    retries={"max_attempts": 8, "mode": "adaptive"},
)
```

This handles Bedrock throttling gracefully, which is important because three agents make parallel LLM calls on every event.
