"""Canonical owner-specific QWEN capability interfaces.

These narrow protocols replace the legacy aggregate skill API. They describe
reasoning and retrieval boundaries only; deterministic policies remain outside
the agent interfaces.

File mappings:
``agent_interfaces/qwen.py`` <- ``frameworkless_app/skills_api/owner_qwen.py``;
``skills_api/owner_qwen.py`` <- ``frameworkless_app/skills_api/owner_qwen.py``;
``skills_api/qwen_agent_rag_loading.py`` <-
``frameworkless_app/skills_api/qwen_agent_rag_loading.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from collections.abc import Awaitable
from typing import Protocol

from crewai_app.domain.contracts.schemas import (
    QwenStrategyCandidateSet,
    QwenSignalHypothesis,
    SerialRagExample,
    SignalEvaluationResult,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradingMessageRelationDecision,
    TradingMessageSynonymDecision,
    TradeThreadCursor,
    PositionReductionHypothesis,
)


class SerialRagLoaderAPI(Protocol):
    """Load hydrated, ordered serial-RAG examples for one source message."""

    async def load(
        self,
        message: TelegramMessageEnvelope,
    ) -> list[SerialRagExample]: ...


class QwenCandidateInferenceAPI(Protocol):
    async def infer_strategy_candidates(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
    ) -> QwenStrategyCandidateSet: ...


class QwenMessageRelationAPI(Protocol):
    """Classify semantic message relations using context and serial RAG."""

    async def classify_message_relation(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
        serial_rag_examples: list[SerialRagExample],
    ) -> TradingMessageRelationDecision: ...


class QwenSynonymInferenceAPI(Protocol):
    """Infer a reviewable trading-message synonym without creating an order."""

    async def infer_synonym(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
    ) -> TradingMessageSynonymDecision: ...


class QwenPositionReductionAPI(Protocol):
    """Interpret a reduce-and-protect instruction without exchange mutation."""

    async def infer_position_reduction(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
    ) -> PositionReductionHypothesis: ...


class SignalEvaluationAPI(Protocol):
    def evaluate(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
        serial_rag_examples: list[SerialRagExample],
        active_trade_cursors: list[TradeThreadCursor],
    ) -> Awaitable[SignalEvaluationResult]: ...


class LegacySignalInferenceAPI(Protocol):
    """Temporary compatibility contract for the pre-CrewAI single-hypothesis path."""

    async def infer_signal(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
    ) -> QwenSignalHypothesis: ...


__all__ = [
    "QwenCandidateInferenceAPI",
    "QwenMessageRelationAPI",
    "QwenPositionReductionAPI",
    "QwenSynonymInferenceAPI",
    "SerialRagLoaderAPI",
    "LegacySignalInferenceAPI",
    "SignalEvaluationAPI",
]
