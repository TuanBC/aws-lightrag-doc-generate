"""LLM and embedding model provider configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from langchain_aws import BedrockEmbeddings, ChatBedrockConverse
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.core.config import get_settings

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Instantiate the configured LLM provider for chat completions."""
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
            max_tokens=4000,
        )

    if provider == "bedrock":
        return ChatBedrockConverse(
            model_id=settings.bedrock_model_id,
            region_name=settings.bedrock_region,
            temperature=0.7,
            max_tokens=4000,
        )

    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")


@lru_cache(maxsize=1)
def get_embedding_model() -> "Embeddings":
    """Instantiate the Bedrock embedding model for Knowledge Base."""
    settings = get_settings()
    return BedrockEmbeddings(
        model_id=settings.bedrock_embed_model_id,
        region_name=settings.bedrock_region,
    )


@lru_cache(maxsize=1)
def get_bedrock_runtime_client():
    """Get boto3 Bedrock runtime client for Knowledge Base operations."""
    import boto3

    settings = get_settings()
    return boto3.client(
        "bedrock-agent-runtime",
        region_name=settings.bedrock_region,
    )


@lru_cache(maxsize=1)
def get_s3_client():
    """Get boto3 S3 client for document uploads."""
    import boto3

    settings = get_settings()
    return boto3.client("s3", region_name=settings.bedrock_region)
