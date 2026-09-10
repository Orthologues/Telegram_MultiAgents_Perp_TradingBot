"""Compatibility aggregate for the pre-CrewAI Ministral API.

Canonical CrewAI review is exposed through agent_interfaces.ministral.
Stop-loss derivation and take-profit protection are deterministic policies or
lifecycle services, not agent-owned mutation capabilities.

File mappings:
``skills_api/ministral_filter.py`` <- ``frameworkless_app/skills_api/ministral_filter.py``;
``agent_interfaces/ministral.py`` <- ``frameworkless_app/skills_api/ministral_filter.py``;
``skills_api/omitted_stop_loss_inference.py`` <-
``frameworkless_app/skills_api/omitted_stop_loss_inference.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from typing import Protocol

from crewai_app.domain.contracts.schemas import (
    FilterDecision,
    MarketAnalysisSnapshot,
    OmittedStopLossDecision,
    PositionLifecycleEvent,
    QwenSignalHypothesis,
    TakeProfitFillEvent,
    TakeProfitProtectionDecision,
    TelegramPromptContext,
)


class MinistralFilterAPI(Protocol):
    """Legacy aggregate retained for frameworkless comparison callers."""

    def infer_omitted_stop_loss(
        self,
        hypothesis: QwenSignalHypothesis,
        market_snapshot: MarketAnalysisSnapshot | None,
    ) -> OmittedStopLossDecision | None: ...

    async def record_execution_event(
        self,
        event: PositionLifecycleEvent,
    ) -> None: ...

    async def protect_entry_after_take_profit(
        self,
        event: TakeProfitFillEvent,
    ) -> TakeProfitProtectionDecision: ...

    async def review(
        self,
        hypothesis: QwenSignalHypothesis,
        prompt_context: TelegramPromptContext,
        market_snapshot: MarketAnalysisSnapshot | None = None,
    ) -> FilterDecision: ...
