"""Owner-specific QWEN skill API."""

from __future__ import annotations

from typing import Protocol

from agentic_perp_trading_bot.schemas import (
    PositionReductionHypothesis,
    QwenSignalHypothesis,
    QwenStrategyCandidateSet,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradingMessageSynonymDecision,
)


class OwnerQwenAPI(Protocol):
    async def infer_strategy_candidates(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext | None = None,
    ) -> QwenStrategyCandidateSet: ...

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

    async def infer_position_reduction(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
    ) -> PositionReductionHypothesis: ...
