"""Typed state and structured outputs for CrewAI trading flows."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from crewai.flow.flow import FlowState
from pydantic import BaseModel, Field, field_validator, model_validator

from crewai_app.domain.contracts.schemas import (
    ApprovedExecutionRequest,
    ClosedTradeOutcome,
    ExchangeId,
    ExchangeNetwork,
    ExchangeTradeState,
    FilterDecision,
    MarketAnalysisSnapshot,
    OwnerId,
    QwenStrategyCandidateSet,
    SerialRagExample,
    StrategyTier,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TestnetVenuePerformanceComparison,
    TradeThreadCursor,
)


class MinistralStrategyReviewSet(BaseModel):
    """One shared Ministral review for every QWEN strategy tier."""

    owner_id: OwnerId
    channel_id: str
    reviewer_model: str = Field(min_length=1)
    reviews: dict[StrategyTier, FilterDecision]

    @field_validator("reviews")
    @classmethod
    def validate_all_tiers(
        cls,
        reviews: dict[StrategyTier, FilterDecision],
    ) -> dict[StrategyTier, FilterDecision]:
        if set(reviews) != set(StrategyTier):
            raise ValueError("Ministral reviews must contain exactly all five strategy tiers")
        return reviews


class SignalEvaluationResult(BaseModel):
    """Structured result returned by the sequential QWEN-Ministral Crew."""

    candidates: QwenStrategyCandidateSet
    reviews: MinistralStrategyReviewSet

    @model_validator(mode="after")
    def validate_identity(self) -> SignalEvaluationResult:
        if self.candidates.owner_id != self.reviews.owner_id:
            raise ValueError("QWEN and Ministral owner IDs must match")
        if self.candidates.channel_id != self.reviews.channel_id:
            raise ValueError("QWEN and Ministral channel IDs must match")
        return self


class ExecutionLiquiditySnapshot(BaseModel):
    """MCP market data required by deterministic pre-execution gates."""

    market: MarketAnalysisSnapshot
    reference_price: Decimal = Field(gt=Decimal("0"))
    order_book_depth_usd: Decimal = Field(ge=Decimal("0"))
    minimum_order_book_depth_usd: Decimal = Field(gt=Decimal("0"))
    expected_slippage_fraction: Decimal = Field(ge=Decimal("0"))
    maximum_expected_slippage_fraction: Decimal = Field(ge=Decimal("0"))

    @property
    def rejection_reasons(self) -> list[str]:
        reasons: list[str] = []
        if self.order_book_depth_usd < self.minimum_order_book_depth_usd:
            reasons.append("insufficient_order_book_depth")
        if self.expected_slippage_fraction > self.maximum_expected_slippage_fraction:
            reasons.append("excessive_expected_slippage")
        return reasons


class DecisionRecord(BaseModel):
    """Flow-only persistence record for approved and rejected decisions."""

    flow_id: str
    owner_id: OwnerId
    channel_id: str
    telegram_message_id: str
    approved_execution_request: ApprovedExecutionRequest | None = None
    rejection_reasons: list[str] = Field(default_factory=list)
    recorded_at: datetime


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
    candidate_set: QwenStrategyCandidateSet | None = None
    ministral_review_set: MinistralStrategyReviewSet | None = None
    market_snapshots: dict[ExchangeId, ExecutionLiquiditySnapshot] = Field(
        default_factory=dict
    )
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


class StrategyOutcome(BaseModel):
    strategy_tier: StrategyTier
    outcome: ClosedTradeOutcome
    counterfactual: bool = False


class StrategyTierPerformanceSummary(BaseModel):
    strategy_tier: StrategyTier
    sample_count: int = Field(ge=0)
    executed_count: int = Field(ge=0)
    counterfactual_count: int = Field(ge=0)
    profitable_count: int = Field(ge=0)
    losing_count: int = Field(ge=0)
    net_pnl_percentage: Decimal


class PerformanceEvaluationState(FlowState):
    """State for matched-venue and five-tier performance evaluation."""

    closed_outcomes: list[ClosedTradeOutcome] = Field(default_factory=list)
    strategy_outcomes: list[StrategyOutcome] = Field(default_factory=list)
    venue_comparison: TestnetVenuePerformanceComparison | None = None
    strategy_summaries: dict[StrategyTier, StrategyTierPerformanceSummary] = Field(
        default_factory=dict
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

    @model_validator(mode="after")
    def reject_unsafe_mainnet(self) -> ExecutionMode:
        if self.mainnet_enabled:
            raise ValueError(
                "mainnet requires a separately reviewed operator-controlled implementation"
            )
        return self

    def permits(self, network: ExchangeNetwork) -> bool:
        return network == ExchangeNetwork.TESTNET and self.testnet_enabled
