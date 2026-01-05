"""Document type classification agent using LLM."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.llm import get_llm
from app.core.prompts import load_prompt
from app.services.document_generator import DocumentType

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of document type classification."""

    document_type: DocumentType
    confidence: float
    reasoning: str


class DocumentClassifierAgent:
    """
    Classifies user requests into appropriate document types.

    Uses LLM to analyze the user's request and determine the best
    matching document type from the available templates.
    """

    def __init__(self):
        self.llm = get_llm()
        self.settings = get_settings()

    async def classify(self, request: str) -> ClassificationResult:
        """
        Classify a user request into a document type.

        Args:
            request: The user's document generation request

        Returns:
            ClassificationResult with detected type, confidence, and reasoning
        """
        logger.info(f"Classifying request: {request[:100]}...")

        # Load and render the classifier prompt
        prompt = load_prompt("document_classifier", request=request)

        # Call LLM
        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        content = self._extract_response_content(response)

        # Parse the JSON response
        result = self._parse_classification(content)
        logger.info(
            f"Classified as {result.document_type.value} with {result.confidence:.0%} confidence"
        )

        return result

    def _extract_response_content(self, response) -> str:
        """Extract text content from LLM response."""
        if hasattr(response, "text") and response.text:
            return response.text

        content = getattr(response, "content", "")
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts = []
            for chunk in content:
                if isinstance(chunk, dict) and "text" in chunk:
                    parts.append(chunk["text"])
                elif hasattr(chunk, "text"):
                    parts.append(chunk.text)
            return "\n".join(parts)

        return str(content)

    def _parse_classification(self, content: str) -> ClassificationResult:
        """Parse the LLM's JSON classification response."""
        try:
            # Extract JSON from response (may have markdown code blocks)
            json_match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(content.strip())

            # Map string to DocumentType enum
            doc_type_str = data.get("document_type", "general").lower()
            doc_type = self._string_to_document_type(doc_type_str)

            return ClassificationResult(
                document_type=doc_type,
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse classification response: {e}")
            # Default to general with low confidence
            return ClassificationResult(
                document_type=DocumentType.GENERAL,
                confidence=0.3,
                reasoning=f"Parse error, defaulting to general: {str(e)}",
            )

    def _string_to_document_type(self, type_str: str) -> DocumentType:
        """Convert string to DocumentType enum."""
        type_map = {
            "srs": DocumentType.SRS,
            "functional_spec": DocumentType.FUNCTIONAL_SPEC,
            "api_docs": DocumentType.API_DOCS,
            "architecture": DocumentType.ARCHITECTURE,
            "general": DocumentType.GENERAL,
        }
        return type_map.get(type_str.lower(), DocumentType.GENERAL)


class ClassificationError(Exception):
    """Error during document classification."""

    pass
