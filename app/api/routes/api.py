"""JSON API routes for technical document generation."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.schemas import (
    CriticReportResponse,
    GeneratedDocumentResponse,
    GenerateDocumentRequest,
    HealthResponse,
    StreamEvent,
    ToolStep,
    UploadDocumentRequest,
    UploadDocumentResponse,
    ValidateDocumentRequest,
    ValidationIssue,
    ValidationResultResponse,
    ValidationSeverity,
)
from app.services.critic_agent import CriticAgent
from app.services.document_generator import (
    DocumentGenerationError,
    DocumentGenerator,
    DocumentType,
)
from app.services.knowledge_base_service import KnowledgeBaseError, KnowledgeBaseService

router = APIRouter(tags=["Document Generation API"])


# =============================================================================
# Health Check
# =============================================================================


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Basic liveness probe."""
    return HealthResponse()


# =============================================================================
# Document Generation
# =============================================================================


@router.post(
    "/v1/documents/generate",
    response_model=GeneratedDocumentResponse,
    summary="Generate a technical document",
)
async def generate_document(
    request: GenerateDocumentRequest,
) -> GeneratedDocumentResponse:
    """
    Generate a technical document using Context7 and Knowledge Base context.

    Supported document types:
    - srs: Software Requirements Specification
    - functional_spec: Functional Specification
    - api_docs: API Documentation
    - architecture: Architecture Document
    """
    try:
        generator = DocumentGenerator()
        doc_type = DocumentType(request.document_type.value)

        result = await generator.generate(
            document_type=doc_type,
            library_name=request.library_name,
            requirements=request.requirements,
            topics=request.topics,
            additional_context=request.additional_context,
        )

        return GeneratedDocumentResponse(
            document_type=request.document_type,
            title=result.title,
            content=result.content,
            library_name=result.library_name,
            topics=result.topics,
            generated_at=result.generated_at,
            metadata=result.metadata,
        )

    except DocumentGenerationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post(
    "/v1/documents/generate/markdown",
    response_class=PlainTextResponse,
    summary="Generate document and return raw markdown",
)
async def generate_document_markdown(
    request: GenerateDocumentRequest,
) -> str:
    """Generate a document and return raw markdown content."""
    try:
        generator = DocumentGenerator()
        doc_type = DocumentType(request.document_type.value)

        result = await generator.generate(
            document_type=doc_type,
            library_name=request.library_name,
            requirements=request.requirements,
            topics=request.topics,
            additional_context=request.additional_context,
        )

        return result.content

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/v1/documents/generate/stream",
    summary="Generate document with streaming tool steps (SSE)",
    response_class=StreamingResponse,
)
async def generate_document_stream(
    request: GenerateDocumentRequest,
) -> StreamingResponse:
    """
    Generate a document with Server-Sent Events for real-time tool step display.

    Streams events of types:
    - step: Tool step started/completed (Context7, KB, Critic)
    - content: Final document content chunks
    - done: Generation complete
    - error: Error occurred
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            generator = DocumentGenerator()
            doc_type = DocumentType(request.document_type.value)
            steps: list[ToolStep] = []

            # Step 1: Context7 Library Lookup
            if request.library_name:
                step = ToolStep(
                    tool_name="resolve-library-id",
                    parameters={"libraryName": request.library_name},
                    status="running",
                )
                yield f"data: {StreamEvent(event_type='step', step=step).model_dump_json()}\n\n"

                # Actually fetch context
                library_context = await generator._get_library_context(
                    request.library_name, request.topics
                )

                step.status = "done"
                step.result_summary = f"Found {len(library_context)} chars of documentation"
                steps.append(step)
                yield f"data: {StreamEvent(event_type='step', step=step).model_dump_json()}\n\n"

            # Step 2: Knowledge Base Search
            if request.requirements:
                step = ToolStep(
                    tool_name="search-knowledge-base",
                    parameters={"query": request.requirements[:100] + "..."},
                    status="running",
                )
                yield f"data: {StreamEvent(event_type='step', step=step).model_dump_json()}\n\n"

                kb_context = await generator._get_kb_context(request.requirements)

                step.status = "done"
                step.result_summary = f"Found {len(kb_context) if kb_context else 0} chars from KB"
                steps.append(step)
                yield f"data: {StreamEvent(event_type='step', step=step).model_dump_json()}\n\n"

            # Step 3: LLM Generation
            step = ToolStep(
                tool_name="generate-document",
                parameters={"type": doc_type.value, "model": "Claude 3.5 Sonnet"},
                status="running",
            )
            yield f"data: {StreamEvent(event_type='step', step=step).model_dump_json()}\n\n"

            result = await generator.generate(
                document_type=doc_type,
                library_name=request.library_name,
                requirements=request.requirements,
                topics=request.topics,
                additional_context=request.additional_context,
            )

            step.status = "done"
            step.result_summary = f"Generated {len(result.content)} chars"
            steps.append(step)
            yield f"data: {StreamEvent(event_type='step', step=step).model_dump_json()}\n\n"

            # Final content
            response = GeneratedDocumentResponse(
                document_type=request.document_type,
                title=result.title,
                content=result.content,
                library_name=result.library_name,
                topics=result.topics,
                generated_at=result.generated_at,
                metadata=result.metadata,
                steps=steps,
            )
            yield f"data: {StreamEvent(event_type='content', content_chunk=response.model_dump_json()).model_dump_json()}\n\n"
            yield f"data: {StreamEvent(event_type='done').model_dump_json()}\n\n"

        except Exception as e:
            yield f"data: {StreamEvent(event_type='error', error=str(e)).model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# Document Validation
# =============================================================================


@router.post(
    "/v1/documents/validate",
    response_model=CriticReportResponse,
    summary="Validate a document for syntax and quality",
)
async def validate_document(
    request: ValidateDocumentRequest,
) -> CriticReportResponse:
    """
    Validate document markdown syntax, mermaid charts, and content quality.

    Returns a detailed critic report with issues and suggestions.
    """
    try:
        critic = CriticAgent()
        report = await critic.full_review(
            content=request.content,
            requirements=request.requirements,
            check_content=request.check_content,
        )

        def convert_result(result) -> ValidationResultResponse:
            return ValidationResultResponse(
                passed=result.passed,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity(i.severity.value),
                        category=i.category,
                        message=i.message,
                        line_number=i.line_number,
                        suggestion=i.suggestion,
                    )
                    for i in result.issues
                ],
                checked_items=result.checked_items,
            )

        return CriticReportResponse(
            overall_passed=report.overall_passed,
            markdown_result=convert_result(report.markdown_result),
            mermaid_result=convert_result(report.mermaid_result),
            content_result=convert_result(report.content_result) if report.content_result else None,
            total_errors=report.total_errors,
            total_warnings=report.total_warnings,
            suggestions=report.suggestions,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post(
    "/v1/documents/validate/markdown",
    response_model=ValidationResultResponse,
    summary="Validate markdown syntax only",
)
async def validate_markdown(
    request: ValidateDocumentRequest,
) -> ValidationResultResponse:
    """Quick markdown syntax validation without LLM check."""
    critic = CriticAgent()
    result = critic.validate_markdown_syntax(request.content)

    return ValidationResultResponse(
        passed=result.passed,
        issues=[
            ValidationIssue(
                severity=ValidationSeverity(i.severity.value),
                category=i.category,
                message=i.message,
                line_number=i.line_number,
                suggestion=i.suggestion,
            )
            for i in result.issues
        ],
        checked_items=result.checked_items,
    )


@router.post(
    "/v1/documents/validate/mermaid",
    response_model=ValidationResultResponse,
    summary="Validate mermaid chart syntax only",
)
async def validate_mermaid(
    request: ValidateDocumentRequest,
) -> ValidationResultResponse:
    """Quick mermaid syntax validation."""
    critic = CriticAgent()
    result = critic.validate_mermaid_charts(request.content)

    return ValidationResultResponse(
        passed=result.passed,
        issues=[
            ValidationIssue(
                severity=ValidationSeverity(i.severity.value),
                category=i.category,
                message=i.message,
                line_number=i.line_number,
                suggestion=i.suggestion,
            )
            for i in result.issues
        ],
        checked_items=result.checked_items,
    )


# =============================================================================
# Knowledge Base Upload
# =============================================================================


@router.post(
    "/v1/documents/upload",
    response_model=UploadDocumentResponse,
    summary="Upload document to Knowledge Base",
)
async def upload_document(
    request: UploadDocumentRequest,
) -> UploadDocumentResponse:
    """
    Upload a document to S3 for Knowledge Base ingestion.

    Note: After upload, a KB sync must be triggered to ingest the document.
    """
    try:
        kb_service = KnowledgeBaseService()
        result = await kb_service.upload_document(
            content=request.content,
            filename=request.filename,
            metadata=request.metadata,
        )

        return UploadDocumentResponse(
            document_id=result.document_id,
            s3_uri=result.s3_uri,
        )

    except KnowledgeBaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# =============================================================================
# LightRAG Graph-based RAG
# =============================================================================


@router.post(
    "/v1/lightrag/index",
    summary="Index document in LightRAG",
)
async def lightrag_index(
    content: str,
    doc_id: str | None = None,
):
    """
    Index a document in LightRAG for graph-based retrieval.

    Extracts entities and relationships, stores in S3.
    """
    try:
        from app.services.lightrag_service import LightRAGService

        service = LightRAGService()
        result = await service.insert(content, doc_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.get(
    "/v1/lightrag/query",
    summary="Query LightRAG knowledge graph",
)
async def lightrag_query(
    query: str,
    mode: str = "hybrid",
    top_k: int = 5,
):
    """
    Query the LightRAG knowledge graph.

    Modes: local, global, hybrid
    """
    try:
        from app.services.lightrag_service import LightRAGService

        service = LightRAGService()
        context = await service.query(query, mode=mode, top_k=top_k)
        return {"query": query, "mode": mode, "context": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get(
    "/v1/lightrag/stats",
    summary="Get LightRAG index statistics",
)
async def lightrag_stats():
    """Get statistics about the LightRAG index."""
    try:
        from app.services.lightrag_service import LightRAGService

        service = LightRAGService()
        return await service.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")


# =============================================================================
# Planning Agent - Document Structure Review Workflow
# =============================================================================


@router.post(
    "/v1/plans/create",
    summary="Create a document plan from user request",
)
async def create_plan(user_request: str):
    """
    Create a new document plan with AI-generated outline.

    The outline can be reviewed, refined with comments, and approved before generation.
    """
    from app.schemas import PlanResponse, SectionOutlineSchema
    from app.services.planning_agent import PlanningAgent

    try:
        agent = PlanningAgent()
        plan = await agent.create_plan(user_request)

        return PlanResponse(
            plan_id=plan.plan_id,
            status=plan.status.value,
            user_request=plan.user_request,
            document_type=plan.document_type,
            title=plan.title,
            sections=[
                SectionOutlineSchema(
                    title=s.title,
                    description=s.description,
                    subsections=s.subsections,
                    estimated_length=s.estimated_length,
                )
                for s in plan.sections
            ],
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            user_comments=plan.user_comments,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan creation failed: {str(e)}")


@router.get(
    "/v1/plans/{plan_id}",
    summary="Get plan details",
)
async def get_plan(plan_id: str):
    """Get a document plan by ID."""
    from app.schemas import PlanResponse, SectionOutlineSchema
    from app.services.planning_agent import PlanningAgent

    agent = PlanningAgent()
    plan = await agent.get_plan(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return PlanResponse(
        plan_id=plan.plan_id,
        status=plan.status.value,
        user_request=plan.user_request,
        document_type=plan.document_type,
        title=plan.title,
        sections=[
            SectionOutlineSchema(
                title=s.title,
                description=s.description,
                subsections=s.subsections,
                estimated_length=s.estimated_length,
            )
            for s in plan.sections
        ],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        user_comments=plan.user_comments,
        final_document=plan.final_document,
    )


@router.post(
    "/v1/plans/{plan_id}/comment",
    summary="Add feedback to refine the outline",
)
async def add_plan_comment(plan_id: str, comment: str):
    """
    Add user feedback to refine the document outline.

    The AI will update the outline based on your comments.
    """
    from app.schemas import PlanResponse, SectionOutlineSchema
    from app.services.planning_agent import PlanningAgent

    agent = PlanningAgent()
    plan = await agent.add_comment(plan_id, comment)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return PlanResponse(
        plan_id=plan.plan_id,
        status=plan.status.value,
        user_request=plan.user_request,
        document_type=plan.document_type,
        title=plan.title,
        sections=[
            SectionOutlineSchema(
                title=s.title,
                description=s.description,
                subsections=s.subsections,
                estimated_length=s.estimated_length,
            )
            for s in plan.sections
        ],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        user_comments=plan.user_comments,
    )


@router.post(
    "/v1/plans/{plan_id}/approve",
    summary="Approve the plan outline",
)
async def approve_plan(plan_id: str):
    """Approve the document plan outline for generation."""
    from app.services.planning_agent import PlanningAgent

    agent = PlanningAgent()
    plan = await agent.approve_plan(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {"message": "Plan approved", "plan_id": plan_id, "status": plan.status.value}


@router.post(
    "/v1/plans/{plan_id}/generate",
    summary="Generate document from approved plan",
)
async def generate_from_plan(plan_id: str):
    """
    Generate the full document based on the approved plan.

    The plan must be approved first before generation.
    """
    from app.schemas import PlanResponse, SectionOutlineSchema
    from app.services.planning_agent import PlanningAgent

    agent = PlanningAgent()
    plan = await agent.generate_from_plan(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found or not approved")

    return PlanResponse(
        plan_id=plan.plan_id,
        status=plan.status.value,
        user_request=plan.user_request,
        document_type=plan.document_type,
        title=plan.title,
        sections=[
            SectionOutlineSchema(
                title=s.title,
                description=s.description,
                subsections=s.subsections,
                estimated_length=s.estimated_length,
            )
            for s in plan.sections
        ],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        user_comments=plan.user_comments,
        final_document=plan.final_document,
    )
