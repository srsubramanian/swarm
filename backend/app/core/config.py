from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "SWARM_"}

    bedrock_region: str = "us-east-1"
    bedrock_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
