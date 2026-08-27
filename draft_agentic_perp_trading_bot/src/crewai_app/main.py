"""Standard CrewAI application entrypoints for the preliminary migration."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from decimal import Decimal

from pydantic import BaseModel, Field

from crewai_app.adapters.aws.persistence.decision_repository import (
    InMemoryDecisionRepository,
)
from crewai_app.crew import CrewModelSettings
from crewai_app.crews.signal_evaluation_crew import CrewSignalEvaluator
from crewai_app.domain.contracts.schemas import (
    ExchangeId,
    SerialRagExample,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradeThreadCursor,
)
from crewai_app.flows.states import ExecutionLiquiditySnapshot, ExecutionMode
from crewai_app.flows.telegram_signal_flow import (
    CompatibilityDeterministicDecisionService,
    TelegramSignalFlow,
)


class PreliminaryRunInput(BaseModel):
    """Local input envelope; production input will arrive through SQS adapters."""

    message: TelegramMessageEnvelope
    prompt_context: TelegramPromptContext
    serial_rag_examples: list[SerialRagExample] = Field(default_factory=list)
    active_trade_cursors: list[TradeThreadCursor] = Field(default_factory=list)
    market_snapshots: dict[ExchangeId, ExecutionLiquiditySnapshot]


def run() -> None:
    """Run one preloaded message through the preliminary Flow with IAM Bedrock."""
    input_path = os.getenv("CREWAI_SIGNAL_INPUT_PATH", "").strip()
    if not input_path:
        raise RuntimeError("CREWAI_SIGNAL_INPUT_PATH is required for preliminary local runs")
    payload = PreliminaryRunInput.model_validate(
        json.loads(Path(input_path).read_text(encoding="utf-8"))
    )
    settings = CrewModelSettings.from_environment()
    flow = TelegramSignalFlow(
        parent_context_loader=_StaticParentContextLoader(payload.prompt_context),
        cursor_context_loader=_StaticCursorContextLoader(
            payload.active_trade_cursors
        ),
        serial_rag_loader=_StaticSerialRagLoader(payload.serial_rag_examples),
        signal_evaluator=CrewSignalEvaluator(settings),
        market_snapshot_loader=_StaticMarketSnapshotLoader(payload.market_snapshots),
        deterministic_decision_service=CompatibilityDeterministicDecisionService(),
        decision_repository=InMemoryDecisionRepository(),
        execution_mode=ExecutionMode(),
        tracing=os.getenv("CREWAI_TRACING_ENABLED", "false").lower() == "true",
    )
    asyncio.run(
        flow.kickoff_async(inputs={"message": payload.message.model_dump(mode="json")})
    )
    print(flow.state.model_dump_json(indent=2))


def replay() -> None:
    raise RuntimeError("replay requires human-approved fixtures and is not implemented")


def train() -> None:
    raise RuntimeError("training is disabled for the preliminary migration")


def test() -> None:
    raise RuntimeError("use the deterministic pytest suite for migration verification")


class _StaticParentContextLoader:
    def __init__(self, context: TelegramPromptContext) -> None:
        self.context = context

    async def load(self, message: TelegramMessageEnvelope) -> TelegramPromptContext:
        return self.context


class _StaticCursorContextLoader:
    def __init__(self, cursors: list[TradeThreadCursor]) -> None:
        self.cursors = cursors

    async def load(self, message: TelegramMessageEnvelope) -> list[TradeThreadCursor]:
        return list(self.cursors)


class _StaticSerialRagLoader:
    def __init__(self, examples: list[SerialRagExample]) -> None:
        self.examples = examples

    async def load(self, message: TelegramMessageEnvelope) -> list[SerialRagExample]:
        return list(self.examples)


class _StaticMarketSnapshotLoader:
    def __init__(
        self,
        snapshots: dict[ExchangeId, ExecutionLiquiditySnapshot],
    ) -> None:
        self.snapshots = snapshots

    async def load(
        self,
        exchange_id: ExchangeId,
        symbol: str,
        reference_price: Decimal,
    ) -> ExecutionLiquiditySnapshot:
        snapshot = self.snapshots[exchange_id]
        if snapshot.market.symbol.upper() != symbol.upper():
            raise ValueError("preloaded market snapshot symbol does not match request")
        if snapshot.reference_price != reference_price:
            raise ValueError("preloaded market reference price does not match request")
        return snapshot
