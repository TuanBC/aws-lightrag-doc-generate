"""LLM-powered wallet report generation."""

from __future__ import annotations

from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader
from langchain_core.language_models.chat_models import BaseChatModel

from app.services.scoring_engine import ScoreComputation


class WalletReportService:
    """Render Prompty templates and invoke the configured LLM."""

    def __init__(self, prompts_dir, llm: BaseChatModel) -> None:
        self.llm = llm
        self.env = Environment(loader=FileSystemLoader(str(prompts_dir)))

    def _render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        template = self.env.get_template(template_name)
        return template.render(**data)

    async def generate_markdown_report(self, computation: ScoreComputation) -> str:
        """Construct prompt payload and call the LLM."""
        combined_features = {
            **computation.onchain_features,
            **computation.offchain_data,
        }
        features_preview = list(combined_features.items())[:20]

        report_data = {
            "wallet_address": computation.wallet_address,
            "credit_score": computation.credit_score,
            "transaction_count": computation.transaction_count,
            "features": combined_features,
            "features_preview": features_preview,
            "offchain_data": computation.offchain_data,
        }
        prompt = self._render_template("wallet_report.prompty", report_data)
        messages = [{"role": "user", "content": prompt}]
        response = await self.llm.ainvoke(messages)

        if hasattr(response, "text") and response.text:
            return response.text

        content = getattr(response, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for chunk in content:
                if isinstance(chunk, dict) and "text" in chunk:
                    parts.append(chunk["text"])
                elif hasattr(chunk, "text"):
                    parts.append(chunk.text)  # type: ignore[attr-defined]
            if parts:
                return "\n".join(parts)

        return "Unable to generate report at this time."
