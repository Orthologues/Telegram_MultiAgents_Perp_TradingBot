"""Ministral validation skill API."""

from __future__ import annotations

from typing import Protocol

from agentic_perp_trading_bot.schemas import (
    FilterDecision,
    MarketAnalysisSnapshot,
    QwenSignalHypothesis,
    TakeProfitFillEvent,
    TakeProfitProtectionDecision,
    TelegramPromptContext,
)


class MinistralFilterAPI(Protocol):
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
