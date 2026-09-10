"""Shared Ministral review interface.

File mappings:
``agent_interfaces/ministral.py`` <- ``frameworkless_app/skills_api/ministral_filter.py``;
``skills_api/ministral_filter.py`` <- ``frameworkless_app/skills_api/ministral_filter.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from typing import Protocol

from crewai_app.domain.contracts.schemas import (
    FilterDecision,
    MarketAnalysisSnapshot,
    QwenSignalHypothesis,
    TelegramPromptContext,
)
class MinistralReviewAPI(Protocol):
    async def review(
        self,
        hypothesis: QwenSignalHypothesis,
        prompt_context: TelegramPromptContext,
        market_snapshot: MarketAnalysisSnapshot | None = None,
    ) -> FilterDecision: ...

__all__ = ["MinistralReviewAPI"]
