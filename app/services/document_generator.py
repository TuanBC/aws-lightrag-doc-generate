"""Document generation service using LLM and context from Context7/KB."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from app.core.config import get_settings
from app.core.llm import get_llm
from app.services.context7_service import Context7Error, Context7Service
from app.services.knowledge_base_service import KnowledgeBaseError, KnowledgeBaseService

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Supported document types."""

    SRS = "srs"
    FUNCTIONAL_SPEC = "functional_spec"
    API_DOCS = "api_docs"
    ARCHITECTURE = "architecture"


@dataclass
class GeneratedDocument:
    """Result of document generation."""

    document_type: DocumentType
    title: str
    content: str
    library_name: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentGenerator:
    """
    Orchestrate technical document generation.

    Combines:
    - Context7 MCP for live library documentation
    - Knowledge Base for uploaded reference documents
    - LLM for document synthesis with Mermaid diagrams
    """

    TEMPLATE_MAP = {
        DocumentType.SRS: "srs_template.prompty",
        DocumentType.FUNCTIONAL_SPEC: "functional_spec.prompty",
        DocumentType.API_DOCS: "api_docs.prompty",
        DocumentType.ARCHITECTURE: "architecture.prompty",
    }

    def __init__(self):
        settings = get_settings()
        self.llm = get_llm()
        self.context7 = Context7Service()
        self.kb_service = KnowledgeBaseService()
        self.env = Environment(loader=FileSystemLoader(str(settings.prompts_dir)))

    def _render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Render a Jinja2 prompt template."""
        try:
            template = self.env.get_template(template_name)
            return template.render(**data)
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            raise DocumentGenerationError(f"Template error: {e}") from e

    async def _get_library_context(
        self,
        library_name: str,
        topics: Optional[List[str]] = None,
    ) -> str:
        """Fetch documentation context from Context7."""
        try:
            return await self.context7.get_full_library_context(
                library_name,
                topics=topics,
            )
        except Context7Error as e:
            logger.warning(f"Context7 error: {e}, continuing without library context")
            return f"Note: Could not fetch documentation for {library_name}."

    async def _get_kb_context(self, query: str) -> str:
        """Fetch context from Knowledge Base."""
        try:
            return await self.kb_service.get_context_for_generation(query)
        except KnowledgeBaseError as e:
            logger.warning(f"KB error: {e}, continuing without KB context")
            return ""

    async def generate(
        self,
        document_type: DocumentType,
        library_name: Optional[str] = None,
        requirements: Optional[str] = None,
        topics: Optional[List[str]] = None,
        additional_context: Optional[str] = None,
    ) -> GeneratedDocument:
        """
        Generate a technical document.

        Args:
            document_type: Type of document to generate
            library_name: Library/framework name for Context7 lookup
            requirements: User-provided requirements or description
            topics: Specific topics to focus on
            additional_context: Extra context from user

        Returns:
            Generated document with content and metadata
        """
        logger.info(f"Generating {document_type.value} document")

        # Gather context
        context_parts = []

        # 1. Context7 library docs
        if library_name:
            library_context = await self._get_library_context(library_name, topics)
            context_parts.append(library_context)

        # 2. Knowledge Base (if configured)
        if requirements:
            kb_context = await self._get_kb_context(requirements)
            if kb_context:
                context_parts.append(kb_context)

        # 3. Additional user context
        if additional_context:
            context_parts.append(f"## Additional Context\n\n{additional_context}")

        # Build prompt data
        prompt_data = {
            "library_name": library_name or "General",
            "requirements": requirements or "",
            "topics": topics or [],
            "context": "\n\n---\n\n".join(context_parts),
            "document_type": document_type.value,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Get template
        template_name = self.TEMPLATE_MAP.get(document_type, "srs_template.prompty")
        prompt = self._render_template(template_name, prompt_data)

        # Call LLM
        logger.info(f"Calling LLM with {len(prompt)} character prompt")
        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])

        # Extract content
        content = self._extract_response_content(response)

        # Self-critique loop: validate and refine until passing or max iterations
        max_iterations = 5
        for iteration in range(max_iterations):
            logger.info(f"Critic validation iteration {iteration + 1}/{max_iterations}")

            # Validate with critic
            from app.services.critic_agent import CriticAgent

            critic = CriticAgent()
            report = await critic.full_review(
                content, requirements=requirements, check_content=False
            )

            if report.overall_passed:
                logger.info(f"Document passed validation on iteration {iteration + 1}")
                break

            # Collect issues for refinement
            issues = []
            for issue in report.markdown_result.issues:
                issues.append(f"[{issue.severity}] {issue.category}: {issue.message}")
            for issue in report.mermaid_result.issues:
                issues.append(f"[{issue.severity}] Mermaid: {issue.message}")

            if not issues:
                logger.info("No specific issues found, accepting document")
                break

            # Refine document based on feedback
            logger.info(f"Refining document based on {len(issues)} issues")
            from app.core.prompts import load_prompt

            refine_prompt = load_prompt(
                "document_refine",
                original_document=content,
                issues="\n".join(f"- {i}" for i in issues),
            )

            refine_response = await self.llm.ainvoke([{"role": "user", "content": refine_prompt}])
            content = self._extract_response_content(refine_response)

        else:
            logger.warning(f"Document did not pass validation after {max_iterations} iterations")

        # Build title
        title = f"{document_type.value.upper().replace('_', ' ')}"
        if library_name:
            title += f" - {library_name}"

        return GeneratedDocument(
            document_type=document_type,
            title=title,
            content=content,
            library_name=library_name,
            topics=topics or [],
            metadata={
                "prompt_length": len(prompt),
                "response_length": len(content),
                "refinement_iterations": iteration + 1 if "iteration" in dir() else 0,
            },
        )

    def _extract_response_content(self, response: Any) -> str:
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

    async def generate_srs(
        self,
        library_name: str,
        requirements: str,
        topics: Optional[List[str]] = None,
    ) -> GeneratedDocument:
        """Generate Software Requirements Specification."""
        return await self.generate(
            document_type=DocumentType.SRS,
            library_name=library_name,
            requirements=requirements,
            topics=topics,
        )

    async def generate_functional_spec(
        self,
        library_name: str,
        features: List[str],
    ) -> GeneratedDocument:
        """Generate Functional Specification."""
        return await self.generate(
            document_type=DocumentType.FUNCTIONAL_SPEC,
            library_name=library_name,
            requirements="\n".join(f"- {f}" for f in features),
            topics=features,
        )


class DocumentGenerationError(Exception):
    """Error during document generation."""

    pass
