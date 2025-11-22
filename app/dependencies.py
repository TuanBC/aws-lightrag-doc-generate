"""Dependency wiring for the FastAPI application."""

from functools import lru_cache
from typing import Optional

from fastapi import HTTPException

from services.credit_scoring_service import CreditScoringService
from services.etherscan_service import EtherscanService
from services.offchain_data_generator import OffchainDataGenerator

from app.core.config import get_settings
from app.core.llm import get_llm
from app.services.cache import InMemoryTTLCache
from app.services.limiter import RateLimiter
from app.services.reporting import WalletReportService
from app.services.scoring_engine import ScoringEngine, ScoreComputation


@lru_cache(maxsize=1)
def get_cache() -> InMemoryTTLCache[ScoreComputation]:
    return InMemoryTTLCache(ttl_seconds=180, max_items=300)


@lru_cache(maxsize=1)
def get_scoring_engine() -> ScoringEngine:
    """Instantiate and cache the scoring engine."""
    settings = get_settings()
    return ScoringEngine(
        etherscan_service=EtherscanService(api_key=settings.etherscan_api_key),
        credit_scoring_service=CreditScoringService(),
        offchain_generator=OffchainDataGenerator(),
        cache=get_cache(),
    )


@lru_cache(maxsize=1)
def get_report_service_optional() -> Optional[WalletReportService]:
    settings = get_settings()
    try:
        llm = get_llm()
    except RuntimeError:
        return None
    return WalletReportService(prompts_dir=settings.prompts_dir, llm=llm)


def require_report_service() -> WalletReportService:
    service = get_report_service_optional()
    if not service:
        raise HTTPException(
            status_code=503, detail="Report generation backend is not configured"
        )
    return service


def report_generation_enabled() -> bool:
    return get_report_service_optional() is not None


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    return RateLimiter(max_requests=25, window_seconds=60)
