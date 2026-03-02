"""Cached LLM instance for agent nodes."""

from functools import lru_cache

from langchain_aws import ChatBedrockConverse

from app.core.config import get_settings


@lru_cache
def get_llm() -> ChatBedrockConverse:
    settings = get_settings()
    return ChatBedrockConverse(
        model=settings.bedrock_model_id,
        region_name=settings.bedrock_region,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
