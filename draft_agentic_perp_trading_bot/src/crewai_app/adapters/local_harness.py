"""Local preloaded-input adapters for the non-production CrewAI harness.

File mappings:
``adapters/local_harness.py`` <- ``main.py`` static loader classes;
``domain/policies/execution_gate.py`` <- ``frameworkless_app/risk_engine/policy.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import List

from crewai_app.domain.contracts.schemas import (
    ExchangeId,
    MarketExecutionSnapshot,
    SerialRagExample,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradeThreadCursor,
)
from crewai_app.domain.policies.execution_gate import validate_market_snapshot
from crewai_app.domain.policies.rag_curation import validated_serial_rag_examples


class StaticParentContextLoader:
    """Return parent context supplied by a local replay input file."""

    def __init__(self, context: TelegramPromptContext) -> None:
        self.context = context

    async def load(self, message: TelegramMessageEnvelope) -> TelegramPromptContext:
        return self.context


class StaticCursorContextLoader:
    """Return preloaded cursor state without reading a live repository."""

    def __init__(self, cursors: List[TradeThreadCursor]) -> None:
        self.cursors = cursors

    async def load(self, message: TelegramMessageEnvelope) -> List[TradeThreadCursor]:
        return list(self.cursors)


class StaticSerialRagLoader:
    """Return manually supplied serial-RAG references for local runs."""

    def __init__(self, examples: List[SerialRagExample]) -> None:
        self.examples = validated_serial_rag_examples(examples)

    async def load(self, message: TelegramMessageEnvelope) -> List[SerialRagExample]:
        return list(self.examples)


class StaticMarketSnapshotLoader:
    """Validate and return preloaded MCP snapshots for a local run."""

    def __init__(self, snapshots: Mapping[ExchangeId, MarketExecutionSnapshot]) -> None:
        self.snapshots = dict(snapshots)

    async def load(
        self,
        exchange_id: ExchangeId,
        symbol: str,
        reference_price: Decimal,
    ) -> MarketExecutionSnapshot:
        try:
            snapshot = self.snapshots[exchange_id]
        except KeyError as exc:
            raise ValueError(f"market snapshot is missing for {exchange_id}") from exc
        validate_market_snapshot(
            snapshot_symbol=snapshot.market.symbol,
            requested_symbol=symbol,
            snapshot_reference_price=snapshot.reference_price,
            reference_price=reference_price,
            current_price=snapshot.market.current_price,
        )
        return snapshot


__all__ = [
    "StaticCursorContextLoader",
    "StaticMarketSnapshotLoader",
    "StaticParentContextLoader",
    "StaticSerialRagLoader",
]
