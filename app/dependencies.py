"""FastAPI dependency injection providers."""

from __future__ import annotations

from functools import lru_cache

from app.services.context7_service import Context7Service
from app.services.critic_agent import CriticAgent
from app.services.document_generator import DocumentGenerator
from app.services.knowledge_base_service import KnowledgeBaseService


@lru_cache(maxsize=1)
def get_document_generator() -> DocumentGenerator:
    """Get cached document generator instance."""
    return DocumentGenerator()


@lru_cache(maxsize=1)
def get_critic_agent() -> CriticAgent:
    """Get cached critic agent instance."""
    return CriticAgent()


@lru_cache(maxsize=1)
def get_knowledge_base_service() -> KnowledgeBaseService:
    """Get cached knowledge base service instance."""
    return KnowledgeBaseService()


@lru_cache(maxsize=1)
def get_context7_service() -> Context7Service:
    """Get cached Context7 service instance."""
    return Context7Service()
