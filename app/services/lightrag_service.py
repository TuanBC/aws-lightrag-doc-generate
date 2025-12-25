"""LightRAG service with S3 JSON storage and Bedrock integration."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.llm import get_s3_client

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Entity extracted from documents."""

    name: str
    entity_type: str
    description: str
    source_doc: Optional[str] = None


@dataclass
class Relationship:
    """Relationship between entities."""

    source: str
    target: str
    relation_type: str
    description: str
    weight: float = 1.0


@dataclass
class LightRAGIndex:
    """In-memory LightRAG index structure."""

    entities: Dict[str, Entity] = field(default_factory=dict)
    relationships: List[Relationship] = field(default_factory=list)
    documents: Dict[str, str] = field(default_factory=dict)  # doc_id -> content
    entity_embeddings: Dict[str, List[float]] = field(default_factory=dict)


class LightRAGService:
    """
    Lightweight Graph-based RAG using S3 for storage.

    Uses Bedrock for:
    - Entity/relationship extraction
    - Embedding generation
    - Query answering

    Stores everything as JSON in S3 for zero-cost persistence.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        index_prefix: str = "lightrag/",
    ):
        settings = get_settings()
        self.bucket_name = bucket_name or settings.lightrag_s3_bucket
        self.index_prefix = index_prefix
        self._s3_client = None
        self._index: Optional[LightRAGIndex] = None
        self._llm = None

    @property
    def s3_client(self):
        if self._s3_client is None:
            self._s3_client = get_s3_client()
        return self._s3_client

    @property
    def llm(self):
        if self._llm is None:
            from app.core.llm import get_llm

            self._llm = get_llm()
        return self._llm

    def _s3_key(self, filename: str) -> str:
        """Build S3 key for index files."""
        return f"{self.index_prefix}{filename}"

    async def _load_index(self) -> LightRAGIndex:
        """Load index from S3 or create new one."""
        if self._index is not None:
            return self._index

        if not self.bucket_name:
            logger.warning("No S3 bucket configured, using in-memory index")
            self._index = LightRAGIndex()
            return self._index

        try:
            # Try to load existing index
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self._s3_key("index.json"),
            )
            data = json.loads(response["Body"].read().decode("utf-8"))

            self._index = LightRAGIndex(
                entities={k: Entity(**v) for k, v in data.get("entities", {}).items()},
                relationships=[Relationship(**r) for r in data.get("relationships", [])],
                documents=data.get("documents", {}),
                entity_embeddings=data.get("entity_embeddings", {}),
            )
            logger.info(f"Loaded LightRAG index: {len(self._index.entities)} entities")

        except self.s3_client.exceptions.NoSuchKey:
            logger.info("No existing index, creating new one")
            self._index = LightRAGIndex()
        except Exception as e:
            logger.warning(f"Error loading index: {e}, creating new one")
            self._index = LightRAGIndex()

        return self._index

    async def _save_index(self) -> None:
        """Save index to S3."""
        if not self.bucket_name or self._index is None:
            return

        data = {
            "entities": {
                k: {
                    "name": v.name,
                    "entity_type": v.entity_type,
                    "description": v.description,
                    "source_doc": v.source_doc,
                }
                for k, v in self._index.entities.items()
            },
            "relationships": [
                {
                    "source": r.source,
                    "target": r.target,
                    "relation_type": r.relation_type,
                    "description": r.description,
                    "weight": r.weight,
                }
                for r in self._index.relationships
            ],
            "documents": self._index.documents,
            "entity_embeddings": self._index.entity_embeddings,
        }

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self._s3_key("index.json"),
            Body=json.dumps(data).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Saved LightRAG index to S3")

    async def _extract_entities(
        self, content: str, doc_id: str
    ) -> tuple[List[Entity], List[Relationship]]:
        """Extract entities and relationships using LLM."""
        from app.core.prompts import load_prompt

        prompt = load_prompt("entity_extraction", content=content[:10000])  # Limit size

        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            text = self._extract_text(response)

            # Parse JSON from response
            import re

            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if not json_match:
                return [], []

            data = json.loads(json_match.group())

            entities = [
                Entity(
                    name=e.get("name", ""),
                    entity_type=e.get("type", "unknown"),
                    description=e.get("description", ""),
                    source_doc=doc_id,
                )
                for e in data.get("entities", [])
                if e.get("name")
            ]

            relationships = [
                Relationship(
                    source=r.get("source", ""),
                    target=r.get("target", ""),
                    relation_type=r.get("type", "related"),
                    description=r.get("description", ""),
                )
                for r in data.get("relationships", [])
                if r.get("source") and r.get("target")
            ]

            return entities, relationships

        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return [], []

    def _extract_text(self, response: Any) -> str:
        """Extract text from LLM response."""
        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return " ".join(
                    c.get("text", "") if isinstance(c, dict) else str(c) for c in content
                )
        return str(response)

    async def insert(self, content: str, doc_id: Optional[str] = None) -> Dict[str, int]:
        """
        Insert document into the graph index.

        Args:
            content: Document content (code, markdown, etc.)
            doc_id: Optional document identifier

        Returns:
            Stats about extracted entities/relationships
        """
        import uuid

        doc_id = doc_id or str(uuid.uuid4())

        index = await self._load_index()

        # Store document
        index.documents[doc_id] = content

        # Extract entities and relationships
        entities, relationships = await self._extract_entities(content, doc_id)

        # Add to index
        for entity in entities:
            key = f"{entity.name}:{entity.entity_type}"
            index.entities[key] = entity

        index.relationships.extend(relationships)

        # Save to S3
        await self._save_index()

        return {
            "doc_id": doc_id,
            "entities_extracted": len(entities),
            "relationships_extracted": len(relationships),
            "total_entities": len(index.entities),
            "total_relationships": len(index.relationships),
        }

    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 5,
    ) -> str:
        """
        Query the knowledge graph.

        Args:
            query: Natural language query
            mode: 'local' (specific entities), 'global' (themes), 'hybrid' (both)
            top_k: Number of relevant entities to include

        Returns:
            Context string for document generation
        """
        index = await self._load_index()

        if not index.entities:
            return "No documents indexed yet."

        # Simple keyword matching for now (can be enhanced with embeddings)
        query_lower = query.lower()
        relevant_entities = []

        for key, entity in index.entities.items():
            score = 0
            if entity.name.lower() in query_lower:
                score += 3
            if any(word in entity.description.lower() for word in query_lower.split()):
                score += 1
            if score > 0:
                relevant_entities.append((entity, score))

        # Sort by relevance
        relevant_entities.sort(key=lambda x: x[1], reverse=True)
        top_entities = [e for e, _ in relevant_entities[:top_k]]

        # Find related relationships
        entity_names = {e.name for e in top_entities}
        relevant_rels = [
            r for r in index.relationships if r.source in entity_names or r.target in entity_names
        ]

        # Build context
        context_parts = ["## Knowledge Graph Context\n"]

        if top_entities:
            context_parts.append("### Entities")
            for entity in top_entities:
                context_parts.append(
                    f"- **{entity.name}** ({entity.entity_type}): {entity.description}"
                )

        if relevant_rels:
            context_parts.append("\n### Relationships")
            for rel in relevant_rels[:10]:
                context_parts.append(
                    f"- {rel.source} --[{rel.relation_type}]--> {rel.target}: {rel.description}"
                )

        # Add source snippets if mode is hybrid or local
        if mode in ("hybrid", "local") and top_entities:
            context_parts.append("\n### Source Snippets")
            seen_docs = set()
            for entity in top_entities[:3]:
                if entity.source_doc and entity.source_doc not in seen_docs:
                    doc_content = index.documents.get(entity.source_doc, "")
                    if doc_content:
                        snippet = (
                            doc_content[:500] + "..." if len(doc_content) > 500 else doc_content
                        )
                        context_parts.append(f"\n```\n{snippet}\n```")
                        seen_docs.add(entity.source_doc)

        return "\n".join(context_parts)

    async def get_stats(self) -> Dict[str, int]:
        """Get index statistics."""
        index = await self._load_index()
        return {
            "documents": len(index.documents),
            "entities": len(index.entities),
            "relationships": len(index.relationships),
        }

    async def clear(self) -> None:
        """Clear the entire index."""
        self._index = LightRAGIndex()
        await self._save_index()
        logger.info("Cleared LightRAG index")


class LightRAGError(Exception):
    """Error from LightRAG service."""

    pass
