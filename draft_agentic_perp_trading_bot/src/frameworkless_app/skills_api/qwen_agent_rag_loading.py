"""Typed API for the QWEN-Agent RAG-loading skill."""

from __future__ import annotations

from typing import Protocol

from frameworkless_app.schemas import (
    OwnerRagProfile,
    QwenStrategyCandidateSet,
    TelegramMessageEnvelope,
    TelegramPromptContext,
)


class QwenAgentRagLoadingAPI(Protocol):
    def load_rag_profile(self) -> OwnerRagProfile: ...

    async def infer_strategy_candidates(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext | None = None,
    ) -> QwenStrategyCandidateSet: ...
