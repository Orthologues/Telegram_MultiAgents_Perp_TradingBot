"""Compatibility aggregate for the pre-CrewAI owner-QWEN API.

Canonical CrewAI capability protocols live in agent_interfaces.qwen. RAG
loading, semantic relation reasoning, synonym inference, and position
reduction are separate capabilities; this aggregate remains only for legacy
callers during migration. Deferred human-labelling persistence is an
application adapter rather than an agent skill.

File mappings:
``skills_api/owner_qwen.py`` <- ``frameworkless_app/skills_api/owner_qwen.py``;
``agent_interfaces/qwen.py`` <- ``frameworkless_app/skills_api/owner_qwen.py``;
``skills_api/qwen_agent_rag_loading.py`` <-
``frameworkless_app/skills_api/qwen_agent_rag_loading.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from typing import Protocol

from crewai_app.domain.contracts.schemas import (
    PositionReductionHypothesis,
    OwnerRagProfile,
    QwenSignalHypothesis,
    QwenStrategyCandidateSet,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradingMessageSynonymDecision,
)


class OwnerQwenAPI(Protocol):
    """Legacy aggregate; the canonical Flow uses separate QWEN interfaces."""

    def load_rag_profile(self) -> OwnerRagProfile: ...

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
