"""Ministral validation skill API.

Predecessor: ``src/frameworkless_app/skills_api/ministral_filter.py``. The
inherited omitted-stop-loss API came from
``src/frameworkless_app/skills_api/omitted_stop_loss_inference.py``; imported
domain contracts remain backed by ``src/frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from typing import Protocol

from crewai_app.domain.contracts.schemas import (
    FilterDecision,
    MarketAnalysisSnapshot,
    PositionLifecycleEvent,
    QwenSignalHypothesis,
    TakeProfitFillEvent,
    TakeProfitProtectionDecision,
    TelegramPromptContext,
)
from crewai_app.skills_api.omitted_stop_loss_inference import (
    OmittedStopLossInferenceAPI,
)


class MinistralFilterAPI(OmittedStopLossInferenceAPI, Protocol):
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
