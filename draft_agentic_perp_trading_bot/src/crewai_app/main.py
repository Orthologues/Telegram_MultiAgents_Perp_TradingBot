"""CrewAI application entrypoint with explicit migration provenance.

File mappings:
``main.py`` <- ``frameworkless_app/orchestrator.py``;
``flows/telegram_signal_flow.py`` <- ``frameworkless_app/orchestrator.py``;
``domain/contracts/{definitions.py,schemas.py}`` <- ``frameworkless_app/schemas.py``;
``domain/policies/execution_gate.py`` <- ``frameworkless_app/risk_engine/policy.py``;
``adapters/telegram/{agent_worker,deduplication,normalizer,pipeline,reply_tree,storage}.py``
<- ``frameworkless_app/telegram_ingestion/{agent_worker,deduplication,normalizer,pipeline,reply_tree,storage}.py``;
``adapters/exchanges/mcp/{exchange_gateway,upstream_contracts,venue_contracts}.py``
<- ``frameworkless_app/mcp_gateway/{exchange_gateway,upstream_contracts,venue_contracts}.py``;
``adapters/aws/execution/{lambda_handler,secrets,upstream_clients}.py``
<- ``frameworkless_app/aws_execution/{lambda_handler,secrets,upstream_clients}.py``.
Legacy files remain intact for comparison.
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
from crewai_app.domain.policies.execution_gate import (
    validate_market_snapshot,
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
    input_path = os.getenv("CREWAI_LOCAL_RUN_INPUT_PATH", "").strip()
    if not input_path:
        raise RuntimeError(
            "CREWAI_LOCAL_RUN_INPUT_PATH is required for preliminary local runs"
        )
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
        tracing=os.getenv("CREWAI_TRACING_ENABLED", "false").strip().lower() == "true",
    )
    asyncio.run(
        flow.kickoff_async(inputs={"message": payload.message.model_dump(mode="json")})
    )
    # Example expected output (abridged; the command prints the complete typed state):
    # {
    #   "selected_owner_id": "owner_a_shu_qin",
    #   "candidate_set": {"candidates": "one entry for each of five tiers"},
    #   "ministral_review_set": {"reviews": "one entry for each of five tiers"},
    #   "decision_persisted": true,
    #   "execution_intent_emitted": false,
    #   "trace_steps": [
    #     "load_parent_messages", "load_active_trade_cursors",
    #     "retrieve_owner_rag_examples", "owner_qwen_inference",
    #     "validate_structured_output", "ministral_review",
    #     "load_market_snapshot", "confidence_selection",
    #     "apply_deterministic_policies", "persist_decision"
    #   ]
    # }
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
        validate_market_snapshot(
            snapshot_symbol=snapshot.market.symbol,
            requested_symbol=symbol,
            snapshot_reference_price=snapshot.reference_price,
            reference_price=reference_price,
            current_price=snapshot.market.current_price,
        )
        return snapshot
