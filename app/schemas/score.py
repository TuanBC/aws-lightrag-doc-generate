"""Schemas representing score requests and responses."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of score components."""

    credit_score: float = Field(
        ..., description="Final credit score between 0 and 1000"
    )
    features: Dict[str, Any] = Field(default_factory=dict)
    offchain_data: Dict[str, Any] = Field(default_factory=dict)
    card_info: Dict[str, Any] = Field(default_factory=dict)
    transaction_count: int = Field(default=0, ge=0)


class ScoreResponse(BaseModel):
    """Structured response returned by the API."""

    wallet_address: str
    breakdown: ScoreBreakdown
    message: Optional[str] = None


class ScoreRequest(BaseModel):
    """Incoming score request payload."""

    wallet_address: str = Field(..., min_length=42, max_length=42)
