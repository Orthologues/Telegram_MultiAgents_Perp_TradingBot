"""Ministral validation skill API."""

from __future__ import annotations

from typing import Protocol

from agentic_perp_trading_bot.schemas import (
    FilterDecision,
    QwenSignalHypothesis,
    TelegramPromptContext,
)


class MinistralFilterAPI(Protocol):
    async def review(
        self,
        hypothesis: QwenSignalHypothesis,
        prompt_context: TelegramPromptContext,
    ) -> FilterDecision: ...
