"""Standard CrewAI application entrypoints for the preliminary migration.

Legacy migration boundary: this app still imports implementations from
``src/frameworkless_app`` through the following bridges:

* ``schemas`` -> domain contracts;
* ``telegram_ingestion`` and ``orchestrator`` -> Telegram adapters and flows;
* ``trade_cursor`` -> lifecycle and persistence adapters;
* ``confidence_engine``, ``ministral_filter``, and ``risk_engine`` -> domain policies;
* ``performance_engine`` -> performance services and persistence;
* ``mcp_gateway`` and ``aws_execution`` -> exchange and AWS adapters;
* ``skills_api`` -> CrewAI agent interfaces.

Migration instruction: do not add new legacy imports. Move each implementation
to its corresponding ``crewai_app`` module, preserve its tested behavior, and
update all callers before removing the legacy package. The migration is complete
when ``src/crewai_app`` has no ``frameworkless_app`` imports and the full test
suite passes.
"""

from __future__ import annotations

import asyncio
import json
import os
from decimal import Decimal
from pathlib import Path

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
    #CHECKPOINT_HUMANREVIEW
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
