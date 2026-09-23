"""Shared Ministral review interface.

File mappings:
``agent_interfaces/ministral/interfaces.py`` <- ``frameworkless_app/skills_api/ministral_filter.py``;
``skills_api/ministral_filter/interfaces.py`` <- ``frameworkless_app/skills_api/ministral_filter.py``;
``domain/contracts/__init__.py`` <- ``frameworkless_app/schemas.py``.
"""

from typing import Protocol

from crewai_app.domain.contracts import (
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
