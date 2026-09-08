"""Owner-specific QWEN skill API."""

from __future__ import annotations

from typing import Protocol

from crewai_app.domain.contracts.schemas import (
    PositionReductionHypothesis,
    QwenSignalHypothesis,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradingMessageSynonymDecision,
)
from crewai_app.skills_api.qwen_agent_rag_loading import QwenAgentRagLoadingAPI


class OwnerQwenAPI(QwenAgentRagLoadingAPI, Protocol):
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
