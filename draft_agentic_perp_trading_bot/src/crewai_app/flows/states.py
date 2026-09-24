"""Typed state and structured outputs for CrewAI trading flows."""

from __future__ import annotations

from datetime import datetime
from crewai.flow.flow import FlowState
from pydantic import BaseModel, Field, field_validator, model_validator

from crewai_app.domain.contracts import (
    ApprovedExecutionRequest,
    ClosedTradeOutcome,
    ExchangeId,
    ExchangeNetwork,
    ExchangeTradeState,
    DecisionRecord,
    FundingRateCycleFilterDecision,
    MarketExecutionSnapshot,
    MinistralStrategyReviewSet,
    OwnerId,
    QwenRagLabellingRecord,
    QwenStrategyCandidateSet,
    SerialRagExample,
    SignalEvaluationResult,
    StrategyOutcome,
    StrategyTierPerformanceSummary,
    StrategyTier,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TestnetVenuePerformanceComparison,
    TradeThreadCursor,
    TradingMessageRelationDecision,
)


# Compatibility names retained for callers that imported the old Flow state.
ExecutionLiquiditySnapshot = MarketExecutionSnapshot


class DeterministicDecisionOutcome(BaseModel):
    approved_execution_request: ApprovedExecutionRequest | None = None
    rejection_reasons: list[str] = Field(default_factory=list)


class TelegramSignalState(FlowState):
    """Canonical state for one normalized Telegram message."""

    message: TelegramMessageEnvelope | None = None
    selected_owner_id: OwnerId | None = None
    prompt_context: TelegramPromptContext | None = None
    serial_rag_examples: list[SerialRagExample] = Field(default_factory=list)
    active_trade_cursors: list[TradeThreadCursor] = Field(default_factory=list)
    relation_decision: TradingMessageRelationDecision | None = None
    labelling_record: QwenRagLabellingRecord | None = None
    candidate_set: QwenStrategyCandidateSet | None = None
    ministral_review_set: MinistralStrategyReviewSet | None = None
    market_snapshots: dict[ExchangeId, ExecutionLiquiditySnapshot] = Field(
        default_factory=dict
    )
    funding_rate_filter_decisions: dict[
        ExchangeId,
        FundingRateCycleFilterDecision,
    ] = Field(default_factory=dict)
    approved_execution_request: ApprovedExecutionRequest | None = None
    rejection_reasons: list[str] = Field(default_factory=list)
    decision_record: DecisionRecord | None = None
    decision_persisted: bool = False
    execution_intent_emitted: bool = False
    trace_steps: list[str] = Field(default_factory=list)


class PositionLifecycleState(FlowState):
    """State for refreshing one parent-linked exchange cursor."""

    cursor_id: str = ""
    exchange_state: ExchangeTradeState | None = None
    cursor: TradeThreadCursor | None = None


class PerformanceEvaluationState(FlowState):
    """State for matched-venue and five-tier performance evaluation."""

    closed_outcomes: list[ClosedTradeOutcome] = Field(default_factory=list)
    strategy_outcomes: list[StrategyOutcome] = Field(default_factory=list)
    venue_comparison: TestnetVenuePerformanceComparison | None = None
    strategy_summaries: dict[StrategyTier, StrategyTierPerformanceSummary] = Field(
        default_factory=dict
    )
    strategy_dimension_summaries: list[StrategyTierPerformanceSummary] = Field(
        default_factory=list
    )
    computed_at: datetime | None = None

    @field_validator("strategy_summaries")
    @classmethod
    def validate_summary_tiers(
        cls,
        summaries: dict[StrategyTier, StrategyTierPerformanceSummary],
    ) -> dict[StrategyTier, StrategyTierPerformanceSummary]:
        if summaries and set(summaries) != set(StrategyTier):
            raise ValueError("performance summaries must cover all five strategy tiers")
        return summaries


class ExecutionMode(BaseModel):
    testnet_enabled: bool = False
    mainnet_enabled: bool = False
    testnet_acceptance_complete: bool = False
    execution_review_complete: bool = False
    operator_authorized: bool = False

    @model_validator(mode="after")
    def reject_unsafe_mainnet(self) -> ExecutionMode:
        if self.mainnet_enabled and not (
            self.testnet_acceptance_complete
            and self.execution_review_complete
            and self.operator_authorized
        ):
            raise ValueError(
                "mainnet requires completed testnet acceptance, execution review, "
                "and explicit operator authorization"
            )
        return self

    def permits(self, network: ExchangeNetwork) -> bool:
        return (
            network == ExchangeNetwork.TESTNET
            and self.testnet_enabled
            or network == ExchangeNetwork.MAINNET
            and self.mainnet_enabled
        )


__all__ = [
    "DecisionRecord",
    "DeterministicDecisionOutcome",
    "ExecutionLiquiditySnapshot",
    "ExecutionMode",
    "MinistralStrategyReviewSet",
    "PerformanceEvaluationState",
    "PositionLifecycleState",
    "SignalEvaluationResult",
    "StrategyOutcome",
    "StrategyTierPerformanceSummary",
    "TelegramSignalState",
]
