"""Server-rendered routes with Etherscan-inspired styling."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.dependencies import (
    get_rate_limiter,
    get_scoring_engine,
    report_generation_enabled,
)
from app.services.limiter import RateLimiter
from app.services.scoring_engine import ScoringEngine


settings = get_settings()
templates = Jinja2Templates(directory=str(settings.template_dir))
router = APIRouter(include_in_schema=False)


def _template_context(
    request: Request,
    page_title: str,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    base_ctx = {"request": request, "page_title": page_title}
    if extra:
        base_ctx.update(extra)
    return base_ctx


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request) -> HTMLResponse:
    """Render the dashboard landing page."""
    return templates.TemplateResponse(
        "home.html",
        _template_context(
            request,
            page_title=settings.app_name,
            extra={"report_enabled": report_generation_enabled()},
        ),
    )


@router.post(
    "/scores",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_score_request(
    request: Request,
    wallet_address: str = Form(..., min_length=42, max_length=42),
    scoring_engine: ScoringEngine = Depends(get_scoring_engine),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> HTMLResponse:
    """Handle the address submission from the landing page."""
    try:
        # Normalize address (ensure lowercase and proper format)
        wallet_address = wallet_address.strip().lower()
        if not wallet_address.startswith("0x"):
            wallet_address = "0x" + wallet_address

        # Validate length after normalization
        if len(wallet_address) != 42:
            return templates.TemplateResponse(
                "home.html",
                _template_context(
                    request,
                    page_title=settings.app_name,
                    extra={
                        "message": f"Invalid address length. Expected 42 characters, got {len(wallet_address)}.",
                        "report_enabled": report_generation_enabled(),
                    },
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        client_ip = request.client.host if request.client else "anonymous"
        if not rate_limiter.allow(client_ip):
            return templates.TemplateResponse(
                "home.html",
                _template_context(
                    request,
                    page_title=settings.app_name,
                    extra={
                        "message": "Rate limit exceeded. Please retry in a moment.",
                        "report_enabled": report_generation_enabled(),
                    },
                ),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        result = await scoring_engine.evaluate_wallet(wallet_address)
        template_name = "score_detail.html" if result.onchain_features else "home.html"

        context = {
            "wallet_address": result.wallet_address,
            "score": result.credit_score,
            "features": result.onchain_features,
            "offchain": result.offchain_data,
            "message": result.message,
            "report_enabled": report_generation_enabled(),
        }

        return templates.TemplateResponse(
            template_name,
            _template_context(
                request,
                page_title=f"Score for {result.wallet_address}",
                extra=context,
            ),
        )
    except Exception as e:
        # Log error and return user-friendly message
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error processing score request: {e}", exc_info=True)

        return templates.TemplateResponse(
            "home.html",
            _template_context(
                request,
                page_title=settings.app_name,
                extra={
                    "message": f"An error occurred: {str(e)}. Please try again.",
                    "report_enabled": report_generation_enabled(),
                },
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
