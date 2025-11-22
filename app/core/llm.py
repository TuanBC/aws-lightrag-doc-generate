"""LLM provider configuration."""

from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain_aws import ChatBedrockConverse
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Instantiate the configured LLM provider."""
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouter provider")
        return ChatOpenAI(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.7,
            max_tokens=2000,
        )

    if provider == "bedrock":
        if not settings.aws_bearer_token:
            raise RuntimeError(
                "AWS_BEARER_TOKEN_BEDROCK is required for Bedrock provider"
            )
        return ChatBedrockConverse(
            model_id=settings.bedrock_model_id,
            region_name=settings.bedrock_region,
            temperature=0.7,
            max_tokens=2000,
        )

    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
