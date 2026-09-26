"""CrewAI application entrypoint with explicit migration provenance.

File mappings:
``main.py`` <- ``frameworkless_app/orchestrator.py``;
``flows/telegram_signal_flow.py`` <- ``frameworkless_app/orchestrator.py``;
``domain/contracts/{schemas.py,execution.py,__init__.py}`` <-
``frameworkless_app/schemas.py``;
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
from pathlib import Path

from pydantic import BaseModel, Field

from crewai_app.adapters.aws.persistence.decision_repository import (
    InMemoryDecisionRepository,
)
from crewai_app.adapters.aws.persistence.message_labelling import (
    DeferredQwenLabellingQueue,
    InMemoryMessageLabellingRepository,
)
from crewai_app.adapters.local_harness import (
    StaticCursorContextLoader,
    StaticMarketSnapshotLoader,
    StaticParentContextLoader,
    StaticSerialRagLoader,
)
from crewai_app.crew import CrewModelSettings
from crewai_app.crews.signal_evaluation_crew import (
    CrewMessageRelationEvaluator,
    CrewSignalEvaluator,
)
from crewai_app.domain.contracts import (
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


# Kept as import aliases for the existing local-harness test surface.
_StaticCursorContextLoader = StaticCursorContextLoader
_StaticMarketSnapshotLoader = StaticMarketSnapshotLoader
_StaticParentContextLoader = StaticParentContextLoader
_StaticSerialRagLoader = StaticSerialRagLoader


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
        relation_evaluator=CrewMessageRelationEvaluator(settings),
        labelling_queue=DeferredQwenLabellingQueue(
            InMemoryMessageLabellingRepository()
        ),
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
    #   "ministral_review_set": {
    #     "reviews": "one entry for each of five tiers",
    #     "selected_strategy_tier": "the approved tier selected by Ministral"
    #   },
    #   "decision_persisted": true,
    #   "execution_intent_emitted": false,
    #   "trace_steps": [
    #     "load_parent_messages", "load_active_trade_cursors",
    #     "retrieve_owner_rag_examples", "owner_qwen_inference",
    #     "validate_structured_output", "ministral_review",
    #     "load_market_snapshot", "ministral_selection", "confidence_scoring",
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
