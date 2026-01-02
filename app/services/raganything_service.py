"""RAG-Anything service with Amazon Bedrock models and S3 persistence.

This service provides multimodal RAG capabilities using:
- LightRAG: Graph-based entity/relationship indexing
- RAG-Anything: Multimodal document processing (PDFs, images, markdown)
- Amazon Nova Pro: Text generation + vision understanding
- Amazon Titan Embed V2: Vector embeddings (1024 dim)
- S3: Zero-cost persistence for index files
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RAGAnythingService:
    """Multimodal RAG service using official LightRAG + RAG-Anything.

    Storage: File-based (NetworkX + NanoVectorDB + JSON) synced to S3.
    Cost: ~$0 infrastructure, pay only for Bedrock usage.
    """

    def __init__(
        self,
        working_dir: Optional[str] = None,
        s3_bucket: Optional[str] = None,
        s3_prefix: Optional[str] = None,
    ):
        settings = get_settings()
        self.working_dir = Path(working_dir or settings.rag_working_dir)
        self.s3_bucket = s3_bucket or settings.lightrag_s3_bucket
        self.s3_prefix = s3_prefix or settings.rag_s3_prefix

        self._lightrag = None
        self._rag = None
        self._s3_client = None
        self._initialized = False

    @property
    def s3_client(self):
        """Lazy-loaded S3 client."""
        if self._s3_client is None:
            import boto3

            settings = get_settings()
            self._s3_client = boto3.client("s3", region_name=settings.bedrock_region)
        return self._s3_client

    async def _bedrock_complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history_messages: List[Dict] = None,
        **kwargs,
    ) -> str:
        """Amazon Nova Pro completion function."""
        from lightrag.llm.bedrock import bedrock_complete_if_cache

        settings = get_settings()
        return await bedrock_complete_if_cache(
            model=settings.bedrock_model_id,
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            **kwargs,
        )

    async def _bedrock_embed(self, texts: List[str]) -> np.ndarray:
        """Amazon Titan Embed V2 embedding function."""
        from lightrag.llm.bedrock import bedrock_embed

        return await bedrock_embed.func(texts)

    async def _vision_complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        image_data: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Amazon Nova Pro vision function for multimodal content.

        Nova Pro supports image input via content blocks.
        """
        from lightrag.llm.bedrock import bedrock_complete_if_cache

        settings = get_settings()

        if image_data:
            # Nova Pro handles images in the prompt content
            # RAG-Anything will format this appropriately
            logger.debug("Processing vision request with image data")

        return await bedrock_complete_if_cache(
            model=settings.bedrock_model_id,
            prompt=prompt,
            system_prompt=system_prompt,
            **kwargs,
        )

    async def _sync_from_s3(self) -> None:
        """Download index files from S3 on cold start."""
        if not self.s3_bucket:
            logger.info("No S3 bucket configured, using local storage only")
            return

        self.working_dir.mkdir(parents=True, exist_ok=True)

        try:
            # List objects in S3 prefix
            paginator = self.s3_client.get_paginator("list_objects_v2")

            for page in paginator.paginate(
                Bucket=self.s3_bucket,
                Prefix=self.s3_prefix,
            ):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    relative_path = key[len(self.s3_prefix) :]
                    local_path = self.working_dir / relative_path

                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    self.s3_client.download_file(self.s3_bucket, key, str(local_path))
                    logger.debug(f"Downloaded {key} -> {local_path}")

            logger.info(f"Synced RAG index from s3://{self.s3_bucket}/{self.s3_prefix}")

        except self.s3_client.exceptions.NoSuchBucket:
            logger.warning(f"S3 bucket {self.s3_bucket} does not exist")
        except Exception as e:
            logger.warning(f"Error syncing from S3: {e}")

    async def _sync_to_s3(self) -> None:
        """Upload index files to S3 after modifications."""
        if not self.s3_bucket:
            return

        try:
            # Walk through working directory and upload all files
            for file_path in self.working_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(self.working_dir)
                    s3_key = f"{self.s3_prefix}{relative_path}"

                    self.s3_client.upload_file(str(file_path), self.s3_bucket, s3_key)
                    logger.debug(f"Uploaded {file_path} -> {s3_key}")

            logger.info(f"Synced RAG index to s3://{self.s3_bucket}/{self.s3_prefix}")

        except Exception as e:
            logger.error(f"Error syncing to S3: {e}")
            raise RAGAnythingError(f"Failed to sync to S3: {e}")

    async def initialize(self) -> "RAGAnythingService":
        """Initialize LightRAG and RAG-Anything with file-based storage."""
        if self._initialized:
            return self

        # Sync existing index from S3
        await self._sync_from_s3()

        # Ensure working directory exists
        self.working_dir.mkdir(parents=True, exist_ok=True)

        try:
            from lightrag import LightRAG
            from lightrag.utils import EmbeddingFunc

            settings = get_settings()

            # Initialize LightRAG with explicit file-based storage
            self._lightrag = LightRAG(
                working_dir=str(self.working_dir),
                llm_model_func=self._bedrock_complete,
                llm_model_name=settings.bedrock_model_id,
                embedding_func=EmbeddingFunc(
                    embedding_dim=1024,  # Titan Embed V2
                    max_token_size=8192,
                    func=self._bedrock_embed,
                ),
                # Explicitly specify all storage backends (file-based - zero cost)
                kv_storage="JsonKVStorage",
                vector_storage="NanoVectorDBStorage",
                graph_storage="NetworkXStorage",
                doc_status_storage="JsonDocStatusStorage",
            )

            # Initialize storage connections
            await self._lightrag.initialize_storages()

            # Initialize pipeline status namespace (required before insert)
            from lightrag.kg.shared_storage import initialize_pipeline_status

            await initialize_pipeline_status()

            logger.info("LightRAG initialized with file-based storage")

            # Initialize RAG-Anything for multimodal support
            try:
                from raganything import RAGAnything

                self._rag = RAGAnything(
                    lightrag=self._lightrag,
                    vision_model_func=self._vision_complete,
                )
                logger.info("RAG-Anything multimodal support enabled")
            except ImportError:
                logger.warning("RAG-Anything not available, using LightRAG only")
                self._rag = None

            self._initialized = True
            return self

        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise RAGAnythingError(f"Initialization failed: {e}")

    async def insert_text(self, content: str, doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Insert text content into the index.

        Args:
            content: Text/markdown content to index
            doc_id: Optional document identifier

        Returns:
            Indexing result with stats
        """
        if not self._initialized:
            await self.initialize()

        try:
            await self._lightrag.ainsert(content)
            await self._sync_to_s3()

            return {
                "status": "success",
                "doc_id": doc_id,
                "content_length": len(content),
            }
        except Exception as e:
            logger.error(f"Insert error: {e}")
            raise RAGAnythingError(f"Insert failed: {e}")

    async def insert_document(self, file_path: str, doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Insert multimodal document (PDF, image, markdown).

        Args:
            file_path: Path to the document file
            doc_id: Optional document identifier

        Returns:
            Indexing result with extracted content info
        """
        if not self._initialized:
            await self.initialize()

        file_path = Path(file_path)
        if not file_path.exists():
            raise RAGAnythingError(f"File not found: {file_path}")

        try:
            if self._rag is not None:
                # Use RAG-Anything for multimodal processing
                await self._rag.insert(str(file_path))
                result = {
                    "status": "success",
                    "doc_id": doc_id,
                    "file_path": str(file_path),
                    "processing": "multimodal",
                }
            else:
                # Fall back to text extraction
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                await self._lightrag.ainsert(content)
                result = {
                    "status": "success",
                    "doc_id": doc_id,
                    "file_path": str(file_path),
                    "processing": "text_only",
                }

            await self._sync_to_s3()
            return result

        except Exception as e:
            logger.error(f"Document insert error: {e}")
            raise RAGAnythingError(f"Document insert failed: {e}")

    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Query the knowledge graph with hybrid retrieval.

        Args:
            query: Natural language query
            mode: Retrieval mode - 'local', 'global', 'hybrid', 'naive'
            top_k: Number of results to retrieve

        Returns:
            Query response with context and answer
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Use LightRAG directly for queries (avoids async event loop conflicts)
            # RAG-Anything is used for multimodal document processing during insert
            from lightrag import QueryParam

            response = await self._lightrag.aquery(query, param=QueryParam(mode=mode))

            return {
                "query": query,
                "mode": mode,
                "response": response,
            }

        except Exception as e:
            logger.error(f"Query error: {e}")
            raise RAGAnythingError(f"Query failed: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self._initialized:
            await self.initialize()

        try:
            # Count files in working directory
            stats = {
                "working_dir": str(self.working_dir),
                "s3_bucket": self.s3_bucket,
                "s3_prefix": self.s3_prefix,
                "initialized": self._initialized,
                "multimodal_enabled": self._rag is not None,
            }

            # Check for index files
            if self.working_dir.exists():
                stats["files"] = [
                    str(f.relative_to(self.working_dir))
                    for f in self.working_dir.rglob("*")
                    if f.is_file()
                ]
                stats["file_count"] = len(stats["files"])

            return stats

        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {"error": str(e)}

    async def clear(self) -> None:
        """Clear the entire index."""
        if self.working_dir.exists():
            shutil.rmtree(self.working_dir)
            self.working_dir.mkdir(parents=True, exist_ok=True)

        self._initialized = False
        self._lightrag = None
        self._rag = None

        # Also clear from S3
        if self.s3_bucket:
            try:
                paginator = self.s3_client.get_paginator("list_objects_v2")
                for page in paginator.paginate(
                    Bucket=self.s3_bucket,
                    Prefix=self.s3_prefix,
                ):
                    for obj in page.get("Contents", []):
                        self.s3_client.delete_object(
                            Bucket=self.s3_bucket,
                            Key=obj["Key"],
                        )
                logger.info("Cleared RAG index from S3")
            except Exception as e:
                logger.warning(f"Error clearing S3: {e}")

        logger.info("Cleared RAG index")


class RAGAnythingError(Exception):
    """Error from RAG-Anything service."""

    pass
