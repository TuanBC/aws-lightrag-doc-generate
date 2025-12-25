"""Server-rendered web routes for document generation UI."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.services.critic_agent import CriticAgent
from app.services.document_generator import DocumentGenerator, DocumentType

settings = get_settings()
templates = Jinja2Templates(directory=str(settings.template_dir))
router = APIRouter(include_in_schema=False)


def _template_context(
    request: Request,
    page_title: str,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build common template context."""
    context = {
        "request": request,
        "page_title": page_title,
        "app_name": settings.app_name,
    }
    if extra:
        context.update(extra)
    return context


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request) -> HTMLResponse:
    """Render the document generation landing page."""
    context = _template_context(
        request,
        "Generate Technical Documents",
        {
            "document_types": [
                {"value": "srs", "label": "Software Requirements Specification (SRS)"},
                {"value": "functional_spec", "label": "Functional Specification"},
                {"value": "api_docs", "label": "API Documentation"},
                {"value": "architecture", "label": "Architecture Document"},
            ],
        },
    )
    return templates.TemplateResponse("home.html", context)


@router.post("/generate", response_class=HTMLResponse)
async def generate_document_page(
    request: Request,
    document_type: str = Form(...),
    library_name: Optional[str] = Form(None),
    requirements: Optional[str] = Form(None),
    topics: Optional[str] = Form(None),
) -> HTMLResponse:
    """Handle document generation form submission."""
    try:
        generator = DocumentGenerator()
        doc_type = DocumentType(document_type)

        # Parse topics if provided
        topic_list = None
        if topics:
            topic_list = [t.strip() for t in topics.split(",") if t.strip()]

        result = await generator.generate(
            document_type=doc_type,
            library_name=library_name or None,
            requirements=requirements or None,
            topics=topic_list,
        )

        # Validate the generated document
        critic = CriticAgent()
        validation = await critic.full_review(result.content, check_content=False)

        context = _template_context(
            request,
            result.title,
            {
                "document": result,
                "validation": validation,
                "success": True,
            },
        )
        return templates.TemplateResponse("document.html", context)

    except Exception as e:
        context = _template_context(
            request,
            "Generation Error",
            {
                "error": str(e),
                "success": False,
            },
        )
        return templates.TemplateResponse("home.html", context)


@router.get("/validate", response_class=HTMLResponse)
async def validate_page(request: Request) -> HTMLResponse:
    """Render the document validation page."""
    context = _template_context(request, "Validate Document")
    return templates.TemplateResponse("validate.html", context)


@router.post("/validate", response_class=HTMLResponse)
async def validate_document_page(
    request: Request,
    content: str = Form(...),
    requirements: Optional[str] = Form(None),
) -> HTMLResponse:
    """Handle document validation form submission."""
    try:
        critic = CriticAgent()
        report = await critic.full_review(
            content=content,
            requirements=requirements,
            check_content=True,
        )

        context = _template_context(
            request,
            "Validation Results",
            {
                "content": content,
                "report": report,
                "success": True,
            },
        )
        return templates.TemplateResponse("validate.html", context)

    except Exception as e:
        context = _template_context(
            request,
            "Validation Error",
            {
                "content": content,
                "error": str(e),
                "success": False,
            },
        )
        return templates.TemplateResponse("validate.html", context)
