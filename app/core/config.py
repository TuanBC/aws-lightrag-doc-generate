"""Application configuration and settings management."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


class Settings(BaseModel):
    """Typed settings loaded from environment variables."""

    # Application
    app_name: str = Field(default="Technical Document Generator")
    environment: str = Field(
        default=os.getenv("ENVIRONMENT", "local"), description="Deployment stage"
    )

    # Context7 MCP
    context7_mcp_url: str = Field(
        default=os.getenv("CONTEXT7_MCP_URL", "https://mcp.context7.com/mcp"),
        description="Context7 remote MCP server URL",
    )
    context7_api_key: Optional[str] = Field(
        default=os.getenv("CONTEXT7_API_KEY"),
        description="Context7 API key for higher rate limits",
    )

    # LLM Provider
    llm_provider: str = Field(
        default=os.getenv("LLM_PROVIDER", "bedrock"),
        description="LLM provider: 'bedrock' or 'openrouter'",
    )

    # Bedrock Chat Model
    bedrock_model_id: str = Field(
        default=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"),
        description="Bedrock chat model ID",
    )
    bedrock_region: str = Field(
        default=os.getenv("BEDROCK_REGION", "us-east-1"),
        description="AWS region for Bedrock",
    )

    # Bedrock Embedding Model
    bedrock_embed_model_id: str = Field(
        default=os.getenv("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0"),
        description="Bedrock embedding model ID",
    )

    # Bedrock Knowledge Base
    bedrock_kb_id: Optional[str] = Field(
        default=os.getenv("BEDROCK_KB_ID"),
        description="Bedrock Knowledge Base ID",
    )
    kb_s3_bucket: Optional[str] = Field(
        default=os.getenv("KB_S3_BUCKET"),
        description="S3 bucket for Knowledge Base documents",
    )

    # LightRAG
    lightrag_s3_bucket: Optional[str] = Field(
        default=os.getenv("LIGHTRAG_S3_BUCKET"),
        description="S3 bucket for LightRAG graph index",
    )

    # OpenRouter (optional fallback)
    openrouter_api_key: Optional[str] = Field(
        default=os.getenv("OPENROUTER_API_KEY"),
        description="OpenRouter API key (optional)",
    )
    openrouter_model: str = Field(
        default=os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet"),
        description="OpenRouter model ID",
    )

    # Paths
    template_dir: Path = Field(
        default=Path(__file__).resolve().parents[1] / "templates",
        description="Templates directory path",
    )
    static_dir: Path = Field(
        default=Path(__file__).resolve().parents[1] / "static",
        description="Static assets directory path",
    )
    prompts_dir: Path = Field(
        default=Path(__file__).resolve().parents[2] / "prompts",
        description="Prompt templates directory",
    )

    model_config = ConfigDict(frozen=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()
