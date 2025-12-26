"""Pydantic schemas for document generation API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Supported document types."""

    SRS = "srs"
    FUNCTIONAL_SPEC = "functional_spec"
    API_DOCS = "api_docs"
    ARCHITECTURE = "architecture"
    GENERAL = "general"


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# =============================================================================
# Request Models
# =============================================================================


class GenerateDocumentRequest(BaseModel):
    """Request to generate a technical document."""

    document_type: DocumentType = Field(
        default=DocumentType.SRS,
        description="Type of document to generate",
    )
    library_name: Optional[str] = Field(
        default=None,
        description="Library/framework name for Context7 lookup",
        examples=["react", "fastapi", "next.js"],
    )
    requirements: Optional[str] = Field(
        default=None,
        description="Requirements or description for the document",
    )
    topics: Optional[List[str]] = Field(
        default=None,
        description="Specific topics to focus on",
    )
    additional_context: Optional[str] = Field(
        default=None,
        description="Additional context or notes",
    )


class ValidateDocumentRequest(BaseModel):
    """Request to validate a document."""

    content: str = Field(
        ...,
        description="Document content to validate",
        min_length=1,
    )
    requirements: Optional[str] = Field(
        default=None,
        description="Requirements to check against",
    )
    check_content: bool = Field(
        default=True,
        description="Whether to use LLM for content quality check",
    )


class UploadDocumentRequest(BaseModel):
    """Request to upload a document to Knowledge Base."""

    content: str = Field(
        ...,
        description="Document content to upload",
    )
    filename: Optional[str] = Field(
        default=None,
        description="Optional filename for the document",
    )
    metadata: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional metadata to attach",
    )


# =============================================================================
# Response Models
# =============================================================================


class ValidationIssue(BaseModel):
    """Single validation issue."""

    severity: ValidationSeverity
    category: str
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


class ValidationResultResponse(BaseModel):
    """Result of a validation check."""

    passed: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    checked_items: int = 0


class CriticReportResponse(BaseModel):
    """Complete critic report for a document."""

    overall_passed: bool
    markdown_result: ValidationResultResponse
    mermaid_result: ValidationResultResponse
    content_result: Optional[ValidationResultResponse] = None
    total_errors: int = 0
    total_warnings: int = 0
    suggestions: List[str] = Field(default_factory=list)


class GeneratedDocumentResponse(BaseModel):
    """Response with generated document."""

    document_type: DocumentType
    title: str
    content: str
    library_name: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    generated_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UploadDocumentResponse(BaseModel):
    """Response after document upload."""

    document_id: str
    s3_uri: str
    message: str = "Document uploaded successfully"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    service: str = "technical-doc-generator"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None


# =============================================================================
# Planning Agent Models
# =============================================================================


class PlanStatus(str, Enum):
    """Status of a document plan."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class SectionOutlineSchema(BaseModel):
    """A section in the document outline."""

    title: str
    description: str
    subsections: List[str] = Field(default_factory=list)
    estimated_length: str = "medium"


class CreatePlanRequest(BaseModel):
    """Request to create a new document plan."""

    user_request: str = Field(
        ...,
        description="Free-form user request describing what document they need",
        min_length=10,
        examples=["Create an API documentation for a REST payment service"],
    )


class AddCommentRequest(BaseModel):
    """Request to add a comment to a plan."""

    comment: str = Field(
        ...,
        description="User feedback or comment on the outline",
        min_length=1,
    )


class PlanResponse(BaseModel):
    """Response with document plan details."""

    plan_id: str
    status: PlanStatus
    user_request: str
    document_type: str
    title: str
    sections: List[SectionOutlineSchema]
    created_at: str
    updated_at: str
    user_comments: List[str] = Field(default_factory=list)
    final_document: Optional[str] = None
