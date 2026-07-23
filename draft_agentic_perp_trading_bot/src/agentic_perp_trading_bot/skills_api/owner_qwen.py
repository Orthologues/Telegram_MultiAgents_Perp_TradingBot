"""Owner-specific QWEN skill API."""

from __future__ import annotations

from typing import Protocol

from agentic_perp_trading_bot.schemas import (
    QwenSignalHypothesis,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradingMessageSynonymDecision,
)


class OwnerQwenAPI(Protocol):
    async def infer_signal(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext | None = None,
    ) -> QwenSignalHypothesis: ...

    async def infer_synonym(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
    ) -> TradingMessageSynonymDecision: ...
