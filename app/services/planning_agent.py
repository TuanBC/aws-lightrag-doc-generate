"""Planning Agent service for document structure generation and review workflow."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.llm import get_llm, get_s3_client

logger = logging.getLogger(__name__)


class PlanStatus(str, Enum):
    """Status of a document plan."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SectionOutline:
    """A section in the document outline."""

    title: str
    description: str
    subsections: List[str] = field(default_factory=list)
    estimated_length: str = "medium"  # short, medium, long


@dataclass
class DocumentPlan:
    """A document generation plan with outline for user review."""

    plan_id: str
    status: PlanStatus
    user_request: str
    document_type: str
    title: str
    sections: List[SectionOutline]
    created_at: str
    updated_at: str
    user_comments: List[str] = field(default_factory=list)
    final_document: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "plan_id": self.plan_id,
            "status": self.status.value,
            "user_request": self.user_request,
            "document_type": self.document_type,
            "title": self.title,
            "sections": [asdict(s) for s in self.sections],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_comments": self.user_comments,
            "final_document": self.final_document,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentPlan":
        """Create from dictionary."""
        sections = [SectionOutline(**s) for s in data.get("sections", [])]
        return cls(
            plan_id=data["plan_id"],
            status=PlanStatus(data["status"]),
            user_request=data["user_request"],
            document_type=data["document_type"],
            title=data["title"],
            sections=sections,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            user_comments=data.get("user_comments", []),
            final_document=data.get("final_document"),
            metadata=data.get("metadata", {}),
        )


class PlanningAgent:
    """
    Agent for generating document structures before full generation.

    Workflow:
    1. User submits request
    2. Agent generates outline/structure
    3. User reviews and provides feedback
    4. Agent refines if needed
    5. User approves
    6. Full document generated based on approved structure
    """

    def __init__(self):
        settings = get_settings()
        self._llm = None
        self._s3_client = None
        self.bucket_name = settings.lightrag_s3_bucket  # Reuse LightRAG bucket
        self.plans_prefix = "plans/"

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    @property
    def s3_client(self):
        if self._s3_client is None:
            self._s3_client = get_s3_client()
        return self._s3_client

    def _s3_key(self, plan_id: str) -> str:
        """Build S3 key for plan storage."""
        return f"{self.plans_prefix}{plan_id}.json"

    async def create_plan(self, user_request: str) -> DocumentPlan:
        """
        Create a new document plan from user request.

        Generates an outline for user review.
        """
        from app.core.prompts import load_prompt

        plan_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        # Generate outline using LLM with prompty template
        prompt = load_prompt("planning_create", user_request=user_request)
        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        outline_data = self._parse_json_response(response)

        # Create sections
        sections = [
            SectionOutline(
                title=s.get("title", "Untitled"),
                description=s.get("description", ""),
                subsections=s.get("subsections", []),
                estimated_length=s.get("estimated_length", "medium"),
            )
            for s in outline_data.get("sections", [])
        ]

        plan = DocumentPlan(
            plan_id=plan_id,
            status=PlanStatus.PENDING_REVIEW,
            user_request=user_request,
            document_type=outline_data.get("document_type", "custom"),
            title=outline_data.get("title", "Document"),
            sections=sections,
            created_at=now,
            updated_at=now,
        )

        await self._save_plan(plan)
        logger.info(f"Created plan {plan_id} with {len(sections)} sections")

        return plan

    async def get_plan(self, plan_id: str) -> Optional[DocumentPlan]:
        """Retrieve a plan by ID."""
        if not self.bucket_name:
            logger.warning("No S3 bucket configured")
            return None

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self._s3_key(plan_id),
            )
            data = json.loads(response["Body"].read().decode("utf-8"))
            return DocumentPlan.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading plan {plan_id}: {e}")
            return None

    async def _save_plan(self, plan: DocumentPlan) -> None:
        """Save plan to S3."""
        if not self.bucket_name:
            logger.warning("No S3 bucket configured, plan not persisted")
            return

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self._s3_key(plan.plan_id),
            Body=json.dumps(plan.to_dict()).encode("utf-8"),
            ContentType="application/json",
        )

    async def add_comment(self, plan_id: str, comment: str) -> Optional[DocumentPlan]:
        """Add user comment and refine the outline."""
        from app.core.prompts import load_prompt

        plan = await self.get_plan(plan_id)
        if not plan:
            return None

        plan.user_comments.append(comment)

        # Refine outline based on feedback
        current_outline = {
            "document_type": plan.document_type,
            "title": plan.title,
            "sections": [asdict(s) for s in plan.sections],
        }

        prompt = load_prompt(
            "planning_refine",
            current_outline=json.dumps(current_outline, indent=2),
            user_comments="\n".join(plan.user_comments),
        )

        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        refined_data = self._parse_json_response(response)

        # Update sections
        plan.sections = [
            SectionOutline(
                title=s.get("title", "Untitled"),
                description=s.get("description", ""),
                subsections=s.get("subsections", []),
                estimated_length=s.get("estimated_length", "medium"),
            )
            for s in refined_data.get("sections", [])
        ]
        plan.title = refined_data.get("title", plan.title)
        plan.updated_at = datetime.utcnow().isoformat()

        await self._save_plan(plan)
        logger.info(f"Refined plan {plan_id} based on user feedback")

        return plan

    async def approve_plan(self, plan_id: str) -> Optional[DocumentPlan]:
        """Approve a plan for document generation."""
        plan = await self.get_plan(plan_id)
        if not plan:
            return None

        plan.status = PlanStatus.APPROVED
        plan.updated_at = datetime.utcnow().isoformat()
        await self._save_plan(plan)

        logger.info(f"Plan {plan_id} approved")
        return plan

    async def generate_from_plan(self, plan_id: str) -> Optional[DocumentPlan]:
        """Generate the full document based on approved plan."""
        from app.services.document_generator import DocumentGenerator, DocumentType

        plan = await self.get_plan(plan_id)
        if not plan or plan.status != PlanStatus.APPROVED:
            return None

        plan.status = PlanStatus.GENERATING
        await self._save_plan(plan)

        try:
            # Build structured prompt from outline
            structure_text = self._outline_to_text(plan)

            generator = DocumentGenerator()

            # Map document type
            doc_type_map = {
                "srs": DocumentType.SRS,
                "functional_spec": DocumentType.FUNCTIONAL_SPEC,
                "api_docs": DocumentType.API_DOCS,
                "architecture": DocumentType.ARCHITECTURE,
            }
            doc_type = doc_type_map.get(plan.document_type, DocumentType.SRS)

            result = await generator.generate(
                document_type=doc_type,
                requirements=plan.user_request,
                additional_context=f"## Document Structure (MUST FOLLOW):\n{structure_text}",
            )

            plan.final_document = result.content
            plan.status = PlanStatus.COMPLETED
            plan.updated_at = datetime.utcnow().isoformat()

        except Exception as e:
            logger.error(f"Generation failed for plan {plan_id}: {e}")
            plan.status = PlanStatus.FAILED
            plan.metadata["error"] = str(e)

        await self._save_plan(plan)
        return plan

    def _outline_to_text(self, plan: DocumentPlan) -> str:
        """Convert outline to text format for LLM."""
        lines = [f"# {plan.title}\n"]
        for i, section in enumerate(plan.sections, 1):
            lines.append(f"## {i}. {section.title}")
            lines.append(f"   {section.description}")
            for j, sub in enumerate(section.subsections, 1):
                lines.append(f"   {i}.{j}. {sub}")
            lines.append("")
        return "\n".join(lines)

    def _parse_json_response(self, response: Any) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        import re

        text = self._extract_text(response)

        # Try to find JSON in response
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback
        return {
            "document_type": "custom",
            "title": "Document",
            "sections": [
                {
                    "title": "Overview",
                    "description": "Introduction and overview",
                    "subsections": [],
                }
            ],
        }

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


class PlanningAgentError(Exception):
    """Error from Planning Agent."""

    pass
