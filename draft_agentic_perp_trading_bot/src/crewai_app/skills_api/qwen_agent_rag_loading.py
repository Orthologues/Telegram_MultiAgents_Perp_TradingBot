"""Typed API for the QWEN-Agent RAG-loading skill.

Predecessor: ``src/frameworkless_app/skills_api/qwen_agent_rag_loading.py``.
Its imported RAG and Telegram contracts remain backed by
``src/frameworkless_app/schemas.py`` through the CrewAI contract facade.
"""

from __future__ import annotations

from typing import Protocol

from crewai_app.domain.contracts.schemas import (
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
