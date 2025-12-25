"""Amazon Bedrock Knowledge Base service for RAG operations."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.llm import get_bedrock_runtime_client, get_s3_client

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Single retrieval result from Knowledge Base."""

    content: str
    score: float
    metadata: Dict[str, Any]
    source_uri: Optional[str] = None


@dataclass
class DocumentUploadResult:
    """Result of document upload to S3."""

    document_id: str
    s3_uri: str
    bucket: str
    key: str


class KnowledgeBaseService:
    """
    Service for interacting with Amazon Bedrock Knowledge Base.

    Provides:
    - Document upload to S3 (for KB ingestion)
    - RAG retrieval for context augmentation
    """

    def __init__(
        self,
        kb_id: Optional[str] = None,
        s3_bucket: Optional[str] = None,
    ):
        settings = get_settings()
        self.kb_id = kb_id or settings.bedrock_kb_id
        self.s3_bucket = s3_bucket or settings.kb_s3_bucket
        self._bedrock_client = None
        self._s3_client = None

    @property
    def bedrock_client(self):
        """Lazy-loaded Bedrock runtime client."""
        if self._bedrock_client is None:
            self._bedrock_client = get_bedrock_runtime_client()
        return self._bedrock_client

    @property
    def s3_client(self):
        """Lazy-loaded S3 client."""
        if self._s3_client is None:
            self._s3_client = get_s3_client()
        return self._s3_client

    async def upload_document(
        self,
        content: str,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> DocumentUploadResult:
        """
        Upload a document to S3 for Knowledge Base ingestion.

        Note: After upload, you need to trigger a KB sync to ingest the document.

        Args:
            content: Document content (text/markdown)
            filename: Optional filename (will be auto-generated if not provided)
            metadata: Optional metadata to attach to the document

        Returns:
            Upload result with document ID and S3 URI
        """
        if not self.s3_bucket:
            raise KnowledgeBaseError("S3 bucket not configured (KB_S3_BUCKET)")

        # Generate document ID and key
        doc_id = str(uuid.uuid4())
        filename = filename or f"{doc_id}.md"
        s3_key = f"documents/{filename}"

        # Prepare metadata
        s3_metadata = metadata or {}
        s3_metadata["document-id"] = doc_id

        logger.info(f"Uploading document to s3://{self.s3_bucket}/{s3_key}")

        # Upload to S3 (sync call wrapped for async interface)
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=content.encode("utf-8"),
            ContentType="text/markdown",
            Metadata=s3_metadata,
        )

        return DocumentUploadResult(
            document_id=doc_id,
            s3_uri=f"s3://{self.s3_bucket}/{s3_key}",
            bucket=self.s3_bucket,
            key=s3_key,
        )

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents from Knowledge Base.

        Args:
            query: Search query text
            top_k: Maximum number of results to return
            min_score: Minimum relevance score threshold

        Returns:
            List of retrieval results with content and metadata
        """
        if not self.kb_id:
            raise KnowledgeBaseError("Knowledge Base ID not configured (BEDROCK_KB_ID)")

        logger.info(f"Retrieving from KB {self.kb_id}: {query[:50]}...")

        try:
            response = self.bedrock_client.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": top_k,
                    }
                },
            )

            results = []
            for item in response.get("retrievalResults", []):
                score = item.get("score", 0.0)
                if score >= min_score:
                    content = item.get("content", {}).get("text", "")
                    metadata = item.get("metadata", {})
                    location = item.get("location", {})
                    source_uri = None

                    if location.get("type") == "S3":
                        source_uri = location.get("s3Location", {}).get("uri")

                    results.append(
                        RetrievalResult(
                            content=content,
                            score=score,
                            metadata=metadata,
                            source_uri=source_uri,
                        )
                    )

            logger.info(f"Retrieved {len(results)} results from KB")
            return results

        except Exception as e:
            logger.error(f"Knowledge Base retrieval error: {e}")
            raise KnowledgeBaseError(f"Retrieval failed: {str(e)}") from e

    async def retrieve_and_generate(
        self,
        query: str,
        model_arn: Optional[str] = None,
    ) -> str:
        """
        Retrieve context and generate response using Bedrock.

        This uses Bedrock's built-in RAG capability.

        Args:
            query: User query
            model_arn: Optional model ARN (uses default if not specified)

        Returns:
            Generated response text
        """
        if not self.kb_id:
            raise KnowledgeBaseError("Knowledge Base ID not configured")

        settings = get_settings()
        if model_arn is None:
            model_arn = f"arn:aws:bedrock:{settings.bedrock_region}::foundation-model/{settings.bedrock_model_id}"

        logger.info(f"Retrieve and generate from KB {self.kb_id}")

        try:
            response = self.bedrock_client.retrieve_and_generate(
                input={"text": query},
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": self.kb_id,
                        "modelArn": model_arn,
                    },
                },
            )

            return response.get("output", {}).get("text", "")

        except Exception as e:
            logger.error(f"Retrieve and generate error: {e}")
            raise KnowledgeBaseError(f"Generation failed: {str(e)}") from e

    async def get_context_for_generation(
        self,
        query: str,
        top_k: int = 5,
    ) -> str:
        """
        Get formatted context string for document generation.

        Args:
            query: Query describing the documentation need
            top_k: Number of documents to retrieve

        Returns:
            Formatted context string for LLM prompt
        """
        results = await self.retrieve(query, top_k=top_k)

        if not results:
            return "No relevant context found in Knowledge Base."

        context_parts = ["## Retrieved Context\n"]
        for i, result in enumerate(results, 1):
            context_parts.append(f"### Source {i} (Score: {result.score:.2f})")
            if result.source_uri:
                context_parts.append(f"*Source: {result.source_uri}*\n")
            context_parts.append(result.content)
            context_parts.append("")

        return "\n".join(context_parts)


class KnowledgeBaseError(Exception):
    """Error from Knowledge Base service."""

    pass
