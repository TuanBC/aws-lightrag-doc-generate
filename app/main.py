"""FastAPI application factory for Technical Document Generator."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router, web_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        summary="AI-powered Technical Document Generator",
        description="""
Generate technical documentation (SRS, Functional Specs) with:
- Context7 MCP integration for live library docs
- Amazon Bedrock Knowledge Base for RAG
- Mermaid diagram generation
- Built-in validation and critic agent
        """,
    )

    app.include_router(web_router)
    app.include_router(api_router, prefix="/api")

    # NOTE: CORS is handled by AWS Lambda Function URL configuration
    # Do NOT add CORSMiddleware here - it causes duplicate headers (*, *)
    # which browsers reject. See: aws/terraform/main.tf -> aws_lambda_function_url.cors

    if settings.static_dir.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(settings.static_dir)),
            name="static",
        )

    return app


app = create_app()
