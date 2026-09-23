"""Shared interfaces for the canonical Telegram signal Flow."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Protocol

from crewai_app.domain.contracts import (
    ApprovedExecutionRequest,
    ExchangeId,
    QwenStrategyCandidateSet,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradeThreadCursor,
)
from crewai_app.flows.states import (
    DecisionRecord,
    DeterministicDecisionOutcome,
    ExecutionLiquiditySnapshot,
    MinistralStrategyReviewSet,
)


class ParentContextLoader(Protocol):
    async def load(self, message: TelegramMessageEnvelope) -> TelegramPromptContext: ...


class CursorContextLoader(Protocol):
    async def load(self, message: TelegramMessageEnvelope) -> list[TradeThreadCursor]: ...


class MarketSnapshotLoader(Protocol):
    async def load(
        self,
        exchange_id: ExchangeId,
        symbol: str,
        reference_price: Decimal,
    ) -> ExecutionLiquiditySnapshot: ...


class DeterministicDecisionService(Protocol):
    async def decide(
        self,
        *,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
        candidates: QwenStrategyCandidateSet,
        reviews: MinistralStrategyReviewSet,
        market_snapshots: Mapping[ExchangeId, ExecutionLiquiditySnapshot],
    ) -> DeterministicDecisionOutcome: ...


class DecisionRepository(Protocol):
    async def save(self, decision: DecisionRecord) -> None: ...


class ExecutionIntentPublisher(Protocol):
    async def publish(self, request: ApprovedExecutionRequest) -> None: ...


__all__ = [
    "CursorContextLoader",
    "DecisionRepository",
    "DeterministicDecisionService",
    "ExecutionIntentPublisher",
    "MarketSnapshotLoader",
    "ParentContextLoader",
]
