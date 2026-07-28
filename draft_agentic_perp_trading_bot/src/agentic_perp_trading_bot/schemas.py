"""Shared schemas for the draft multi-agent perpetual futures trading bot."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator


class OwnerId(StrEnum):
    OWNER_A_SHU_QIN = "owner_a_shu_qin"
    OWNER_B_LAO_TU = "owner_b_lao_tu"
    OWNER_C_BI_JIA_SUO = "owner_c_bi_jia_suo"
    OWNER_D_A_ZHU = "owner_d_a_zhu"


class AssetGroup(StrEnum):
    BTC_ETH = "btc_eth"
    ALTS = "alts"
    ALTS_TRADFI = "alts_tradfi"
    CRYPTO = "crypto"
    TRADFI = "tradfi"
    MIXED = "mixed"


class StrategyTier(StrEnum):
    ULTRA_CONSERVATIVE = "ultra_conservative"
    CONSERVATIVE = "conservative"
    INTERMEDIATE = "intermediate"
    RADICAL = "radical"
    ULTRA_RADICAL = "ultra_radical"


class LifecycleStrategySource(StrEnum):
    INITIAL_CONFIDENCE = "initial_confidence"
    TELEGRAM_TRANSITION = "telegram_transition"


class IntentType(StrEnum):
    NEW_ORDER = "new_order"
    ADD_POSITION = "add_position"
    UPDATE_STOP_LOSS = "update_stop_loss"
    UPDATE_TAKE_PROFIT = "update_take_profit"
    CLOSE_POSITION = "close_position"
    IGNORE = "ignore"


class TradeAction(StrEnum):
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    REDUCE_LONG = "reduce_long"
    REDUCE_SHORT = "reduce_short"


class PositionDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


class TakeProfitLevel(StrEnum):
    TP1 = "TP1"
    TP2 = "TP2"
    TP3 = "TP3"


class TakeProfitProtectionAction(StrEnum):
    MOVE_TO_PROTECTED_ENTRY = "move_to_protected_entry"
    MOVE_TO_TP1 = "move_to_tp1"
    NO_CHANGE = "no_change"


class ExchangeId(StrEnum):
    BITGET = "bitget"
    HYPERLIQUID = "hyperliquid"


class TradeCursorStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class MarketLiquidityTier(StrEnum):
    LARGE = "large"
    MID = "mid"
    SMALL = "small"


class IndicatorTimeframe(StrEnum):
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"


class DeduplicationScope(StrEnum):
    MULTIMODAL_INPUT = "multimodal_input"
    TRADING_SIGNAL = "trading_signal"


class IngestionTransport(StrEnum):
    AG2_TELEGRAM_AGENT = "ag2_telegram_agent"


class DeduplicationDecision(BaseModel):
    scope: DeduplicationScope
    is_duplicate: bool
    dedup_key: str
    matched_key: str | None = None
    reasons: list[str] = Field(default_factory=list)


class TelegramAgentRetrievedMessage(BaseModel):
    """Message shape returned by AG2's TelegramRetrieveTool."""

    id: str = Field(pattern=r"^[0-9]+$")
    date: datetime
    from_id: str | None = None
    text: str | None = None
    reply_to_msg_id: str | None = None
    forward_from: str | None = None
    edit_date: datetime | None = None
    media: bool = False
    entities: list[dict[str, Any]] | None = None


class TelegramAgentRetrievalBatch(BaseModel):
    telegram_chat_id: str
    message_count: int = Field(ge=0)
    messages: list[TelegramAgentRetrievedMessage] = Field(default_factory=list)
    start_time: str

    @model_validator(mode="after")
    def validate_message_count(self) -> Self:
        if self.message_count != len(self.messages):
            raise ValueError(
                f"message_count={self.message_count} does not match "
                f"messages={len(self.messages)}"
            )
        return self


class TelegramAgentChannelConfig(BaseModel):
    """One AG2 TelegramAgent is configured for one target Telegram chat."""

    channel_id: str
    telegram_chat_id: str
    maximum_messages: int = Field(default=100, ge=1, le=1000)


class TelegramMessageEnvelope(BaseModel):
    owner_id: OwnerId
    channel_id: str
    asset_group: AssetGroup
    telegram_message_id: str
    received_at: datetime
    source_transport: IngestionTransport = IngestionTransport.AG2_TELEGRAM_AGENT
    telegram_chat_id: str | None = None
    source_timestamp: datetime | None = None
    sender_id: str | None = None
    reply_to_message_id: str | None = None
    parent_messages: list[str] = Field(default_factory=list)
    forwarded_from_id: str | None = None
    edited_at: datetime | None = None
    raw_text: str | None = None
    raw_media_present: bool = False
    media_s3_uri: str | None = None
    content_hash: str | None = None
    media_hashes: list[str] = Field(default_factory=list)
    dedup_key: str | None = None
    language_hint: str = "zh"
    strategy_tier_hint: StrategyTier | None = None

    @field_validator("parent_messages")
    @classmethod
    def validate_parent_messages(cls, message_ids: list[str]) -> list[str]:
        if any(not message_id.isdigit() for message_id in message_ids):
            raise ValueError("parent_messages must contain numeric Telegram message IDs")
        if len(message_ids) != len(set(message_ids)):
            raise ValueError("parent_messages must not contain duplicate message IDs")
        if message_ids != sorted(message_ids, key=int):
            raise ValueError("parent_messages must be in chronological order")
        return message_ids


class ExchangeTradeState(BaseModel):
    """MCP-observed live orders and positions for one exchange trading pair."""

    exchange_id: ExchangeId
    symbol: str = Field(min_length=1)
    direction: PositionDirection
    active_order_ids: set[str] = Field(default_factory=set)
    open_position_ids: set[str] = Field(default_factory=set)
    observed_at: datetime

    @field_validator("active_order_ids", "open_position_ids")
    @classmethod
    def validate_exchange_ids(cls, identifiers: set[str]) -> set[str]:
        if any(not identifier.strip() for identifier in identifiers):
            raise ValueError("exchange order and position IDs must not be blank")
        return identifiers


class PositionLifecycleStrategy(BaseModel):
    """Persisted confidence-selected policy for one position lifecycle."""

    strategy_tier: StrategyTier
    confidence: float = Field(ge=0.0, le=1.0)
    source_confidence: float = Field(ge=0.0, le=1.0)
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    performance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    formula_version: str = Field(min_length=1)
    owner_weight: float = Field(ge=0.0)
    asset_group_weight: float = Field(ge=0.0)
    position_notional_usdt: Decimal = Field(ge=Decimal("0"))
    leverage: int = Field(ge=1, le=125)
    source: LifecycleStrategySource
    source_telegram_message_id: str = Field(pattern=r"^[0-9]+$")
    selected_at: datetime
    revision: int = Field(default=0, ge=0)
    reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_revision_source(self) -> Self:
        if (
            self.source == LifecycleStrategySource.INITIAL_CONFIDENCE
            and self.revision != 0
        ):
            raise ValueError("an initial confidence policy must use revision 0")
        if (
            self.source == LifecycleStrategySource.TELEGRAM_TRANSITION
            and self.revision == 0
        ):
            raise ValueError("a Telegram strategy transition must increment revision")
        return self


class TradeThreadCursor(BaseModel):
    """Concurrent live trade thread selected through Telegram parent messages."""

    cursor_id: str = Field(min_length=1)
    owner_id: OwnerId
    channel_id: str
    origin_message_id: str = Field(pattern=r"^[0-9]+$")
    message_ids: list[str] = Field(min_length=1)
    exchange_id: ExchangeId
    symbol: str = Field(min_length=1)
    direction: PositionDirection
    active_order_ids: set[str] = Field(default_factory=set)
    open_position_ids: set[str] = Field(default_factory=set)
    lifecycle_strategy: PositionLifecycleStrategy
    position_was_opened: bool = False
    status: TradeCursorStatus = TradeCursorStatus.ACTIVE
    opened_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    version: int = Field(default=0, ge=0)

    @field_validator("message_ids")
    @classmethod
    def validate_cursor_message_ids(cls, message_ids: list[str]) -> list[str]:
        if any(not message_id.isdigit() for message_id in message_ids):
            raise ValueError("trade cursor message_ids must be numeric")
        if len(message_ids) != len(set(message_ids)):
            raise ValueError("trade cursor message_ids must not contain duplicates")
        if message_ids != sorted(message_ids, key=int):
            raise ValueError("trade cursor message_ids must be chronological")
        return message_ids

    @model_validator(mode="after")
    def validate_cursor_lifecycle(self) -> Self:
        if self.origin_message_id not in self.message_ids:
            raise ValueError("origin_message_id must be included in message_ids")
        if self.lifecycle_strategy.source_telegram_message_id not in self.message_ids:
            raise ValueError(
                "lifecycle strategy source message must be included in message_ids"
            )
        if (
            self.lifecycle_strategy.revision == 0
            and self.lifecycle_strategy.source_telegram_message_id
            != self.origin_message_id
        ):
            raise ValueError(
                "the initial lifecycle strategy must originate from the cursor root"
            )
        if self.status == TradeCursorStatus.CLOSED:
            if not self.position_was_opened:
                raise ValueError("a cursor cannot close before a position has opened")
            if self.active_order_ids or self.open_position_ids:
                raise ValueError("a closed cursor cannot retain active orders or positions")
            if self.closed_at is None:
                raise ValueError("a closed cursor requires closed_at")
        elif self.closed_at is not None:
            raise ValueError("an active cursor cannot have closed_at")
        return self


class TelegramPromptMessage(BaseModel):
    """ID-labeled source message representation passed into an agent prompt."""

    telegram_message_id: str
    source_timestamp: datetime | None = None
    sender_id: str | None = None
    reply_to_message_id: str | None = None
    raw_text: str | None = None
    raw_media_present: bool = False
    media_s3_uri: str | None = None

    @classmethod
    def from_envelope(cls, message: TelegramMessageEnvelope) -> Self:
        return cls(
            telegram_message_id=message.telegram_message_id,
            source_timestamp=message.source_timestamp,
            sender_id=message.sender_id,
            reply_to_message_id=message.reply_to_message_id,
            raw_text=message.raw_text,
            raw_media_present=message.raw_media_present,
            media_s3_uri=message.media_s3_uri,
        )


class TelegramPromptContext(BaseModel):
    """Current Telegram input plus ordered parent messages for model context."""

    current_message: TelegramMessageEnvelope
    parent_messages: list[TelegramPromptMessage] = Field(default_factory=list)
    active_trade_cursors: list[TradeThreadCursor] = Field(default_factory=list)

    @classmethod
    def from_message(
        cls,
        message: TelegramMessageEnvelope,
        parent_messages: list[TelegramPromptMessage] | None = None,
    ) -> Self:
        if parent_messages is None:
            parent_messages = [
                TelegramPromptMessage(telegram_message_id=message_id)
                for message_id in message.parent_messages
            ]
        return cls(
            current_message=message,
            parent_messages=list(parent_messages),
        )

    def to_prompt_messages(self) -> list[dict[str, Any]]:
        """Serialize parent and current messages with explicit Telegram IDs."""
        prompt_messages = [
            {"role": "parent", **parent.model_dump(mode="json")}
            for parent in self.parent_messages
        ]
        current = TelegramPromptMessage.from_envelope(self.current_message).model_dump(
            mode="json"
        )
        current["parent_message_ids"] = [
            parent.telegram_message_id for parent in self.parent_messages
        ]
        current["active_trade_cursors"] = [
            cursor.model_dump(mode="json") for cursor in self.active_trade_cursors
        ]
        prompt_messages.append({"role": "current", **current})
        return prompt_messages


class TelegramAgentPollBatch(BaseModel):
    channel_id: str
    telegram_chat_id: str
    messages: list[TelegramMessageEnvelope] = Field(default_factory=list)


class TelegramIngestionRecord(BaseModel):
    """Durable metadata record produced before downstream model delivery."""

    message: TelegramMessageEnvelope
    input_deduplication: DeduplicationDecision


class QwenSignalHypothesis(BaseModel):
    owner_id: OwnerId
    channel_id: str
    asset_group: AssetGroup
    model_id: str | None = None
    strategy_tier: StrategyTier
    intent_type: IntentType
    symbol: str | None = None
    direction: str | None = None
    entries: list[Decimal] = Field(default_factory=list)
    stop_loss: Decimal | None = None
    take_profit: list[Decimal] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    source_dedup_key: str | None = None


class QwenStrategyCandidateSet(BaseModel):
    """One owner QWEN interpretation expanded into all five strategy tiers."""

    owner_id: OwnerId
    channel_id: str
    asset_group: AssetGroup
    model_id: str
    interpretation_confidence: float = Field(ge=0.0, le=1.0)
    candidates: dict[StrategyTier, QwenSignalHypothesis]
    source_dedup_key: str | None = None

    @model_validator(mode="after")
    def validate_complete_consistent_candidates(self) -> Self:
        supplied = set(self.candidates)
        required = set(StrategyTier)
        if supplied != required:
            missing = sorted(tier.value for tier in required - supplied)
            unexpected = sorted(tier.value for tier in supplied - required)
            raise ValueError(
                "candidates must contain all five strategy tiers; "
                f"missing={missing}, unexpected={unexpected}"
            )

        expected_identity = (self.owner_id, self.channel_id, self.asset_group)
        for tier, candidate in self.candidates.items():
            candidate_identity = (
                candidate.owner_id,
                candidate.channel_id,
                candidate.asset_group,
            )
            if candidate_identity != expected_identity:
                raise ValueError(f"{tier.value} candidate has inconsistent source identity")
            if candidate.strategy_tier != tier:
                raise ValueError(f"{tier.value} candidate has a mismatched strategy_tier")
            if candidate.model_id != self.model_id:
                raise ValueError(f"{tier.value} candidate has a mismatched model_id")
        return self


class TechnicalIndicatorSnapshot(BaseModel):
    """MCP-supplied indicator values used by deterministic Ministral policy."""

    kdj_k: Decimal
    kdj_d: Decimal
    kdj_j: Decimal
    bollinger_upper: Decimal = Field(gt=Decimal("0"))
    bollinger_middle: Decimal = Field(gt=Decimal("0"))
    bollinger_lower: Decimal = Field(gt=Decimal("0"))
    average_true_range: Decimal = Field(ge=Decimal("0"))

    @model_validator(mode="after")
    def validate_bollinger_bands(self) -> Self:
        if not (
            self.bollinger_lower
            <= self.bollinger_middle
            <= self.bollinger_upper
        ):
            raise ValueError(
                "Bollinger bands must satisfy lower <= middle <= upper"
            )
        return self


class MarketAnalysisSnapshot(BaseModel):
    """Typed Bitget/Hyperliquid MCP input for Ministral validation."""

    exchange_id: ExchangeId
    symbol: str = Field(min_length=1)
    current_price: Decimal = Field(gt=Decimal("0"))
    market_cap_usd: Decimal = Field(gt=Decimal("0"))
    quote_volume_24h_usd: Decimal = Field(ge=Decimal("0"))
    indicators: dict[IndicatorTimeframe, TechnicalIndicatorSnapshot]
    observed_at: datetime

    @field_validator("indicators")
    @classmethod
    def validate_indicator_timeframes(
        cls,
        indicators: dict[IndicatorTimeframe, TechnicalIndicatorSnapshot],
    ) -> dict[IndicatorTimeframe, TechnicalIndicatorSnapshot]:
        required = set(IndicatorTimeframe)
        supplied = set(indicators)
        if supplied != required:
            missing = sorted(timeframe.value for timeframe in required - supplied)
            unexpected = sorted(timeframe.value for timeframe in supplied - required)
            raise ValueError(
                "indicators must contain exactly 5m, 15m, 1h, and 4h; "
                f"missing={missing}, unexpected={unexpected}"
            )
        return indicators


class OmittedStopLossDecision(BaseModel):
    """Deterministic stop-loss derived at the Ministral boundary."""

    stop_loss: Decimal = Field(gt=Decimal("0"))
    distance_fraction: Decimal = Field(
        ge=Decimal("0.0125"),
        le=Decimal("0.075"),
    )
    liquidity_tier: MarketLiquidityTier
    volatility_score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    market_snapshot: MarketAnalysisSnapshot
    policy_version: str
    reasoning_budget_ms: int = Field(default=1000, ge=1, le=1000)
    evidence: list[str] = Field(default_factory=list)


class TradingMessageSynonymDecision(BaseModel):
    """Reviewable baseline-synonym inference, never an execution command."""

    owner_id: OwnerId
    channel_id: str
    telegram_message_id: str
    baseline_signal: str | None = None
    matched_synonym: str | None = None
    conditional_strategy_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    needs_human_review: bool = True


class PositionReductionHypothesis(BaseModel):
    """Reviewable QWEN interpretation of a reduce-and-protect instruction."""

    owner_id: OwnerId
    channel_id: str
    telegram_message_id: str
    symbol: str | None = None
    direction: str | None = None
    selected_reduction_fraction: Decimal | None = Field(
        default=None,
        ge=Decimal("0.30"),
        le=Decimal("0.40"),
    )
    minimum_reduction_fraction: Decimal = Field(
        default=Decimal("0.30"),
        ge=Decimal("0.30"),
        le=Decimal("0.30"),
    )
    maximum_reduction_fraction: Decimal = Field(
        default=Decimal("0.40"),
        ge=Decimal("0.40"),
        le=Decimal("0.40"),
    )
    quantity_basis: Literal[
        "maximum_total_position_quantity"
    ] = "maximum_total_position_quantity"
    stop_loss_profit_offset_fraction: Decimal = Field(
        default=Decimal("0.0015"),
        ge=Decimal("0.0015"),
        le=Decimal("0.0015"),
    )
    resize_unfilled_take_profit_orders: Literal[True] = True
    take_profit_labels: tuple[
        Literal["TP1"],
        Literal["TP2"],
        Literal["TP3"],
    ] = ("TP1", "TP2", "TP3")
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    needs_human_review: bool = True


class TakeProfitFillEvent(BaseModel):
    """Authenticated MCP event used by the Ministral protection policy."""

    event_id: str = Field(min_length=1)
    exchange_id: ExchangeId
    symbol: str = Field(min_length=1)
    position_id: str = Field(min_length=1)
    direction: PositionDirection
    triggered_level: TakeProfitLevel
    configured_levels: list[TakeProfitLevel]
    filled_levels: list[TakeProfitLevel]
    average_entry_price: Decimal = Field(gt=Decimal("0"))
    tp1_price: Decimal = Field(gt=Decimal("0"))
    current_stop_loss: Decimal | None = Field(default=None, gt=Decimal("0"))
    occurred_at: datetime
    source: Literal["mcp_take_profit_fill"] = "mcp_take_profit_fill"

    @model_validator(mode="after")
    def validate_take_profit_sequence(self) -> Self:
        level_order = (
            TakeProfitLevel.TP1,
            TakeProfitLevel.TP2,
            TakeProfitLevel.TP3,
        )
        for field_name, levels in (
            ("configured_levels", self.configured_levels),
            ("filled_levels", self.filled_levels),
        ):
            if len(levels) != len(set(levels)):
                raise ValueError(f"{field_name} must not contain duplicates")
            expected = [level for level in level_order if level in levels]
            if levels != expected:
                raise ValueError(f"{field_name} must be ordered TP1, TP2, TP3")
        if not set(self.filled_levels).issubset(self.configured_levels):
            raise ValueError("filled_levels must be a subset of configured_levels")
        if self.triggered_level not in self.filled_levels:
            raise ValueError("triggered_level must be present in filled_levels")
        if self.triggered_level != self.filled_levels[-1]:
            raise ValueError("triggered_level must be the latest filled level")
        if self.triggered_level == TakeProfitLevel.TP2 and self.filled_levels[:2] != [
            TakeProfitLevel.TP1,
            TakeProfitLevel.TP2,
        ]:
            raise ValueError("TP2 protection requires TP1 to have filled first")
        if self.direction == PositionDirection.LONG:
            if self.tp1_price <= self.average_entry_price:
                raise ValueError("long TP1 price must be above average entry")
        elif self.tp1_price >= self.average_entry_price:
            raise ValueError("short TP1 price must be below average entry")
        return self


class TakeProfitProtectionDecision(BaseModel):
    """Typed Ministral decision passed to the MCP execution boundary."""

    event_id: str
    exchange_id: ExchangeId
    symbol: str
    position_id: str
    action: TakeProfitProtectionAction
    requested_stop_loss: Decimal | None = Field(default=None, gt=Decimal("0"))
    trigger_level: TakeProfitLevel
    policy_version: str
    idempotency_key: str
    reasons: list[str] = Field(default_factory=list)


class CanonicalTradeIntent(BaseModel):
    owner_id: OwnerId
    channel_id: str
    asset_group: AssetGroup
    strategy_tier: StrategyTier
    symbol: str
    action: TradeAction
    order_type: str
    entries: list[Decimal]
    stop_loss: Decimal | None = None
    take_profit: list[Decimal] = Field(default_factory=list)
    target_exchanges: list[ExchangeId]
    signal_dedup_key: str | None = None

    @field_validator("target_exchanges")
    @classmethod
    def validate_target_exchanges(
        cls,
        exchange_ids: list[ExchangeId],
    ) -> list[ExchangeId]:
        if not exchange_ids:
            raise ValueError("target_exchanges must not be empty")
        if len(exchange_ids) != len(set(exchange_ids)):
            raise ValueError("target_exchanges must not contain duplicates")
        return exchange_ids


class FilterDecision(BaseModel):
    status: str
    quality_score: float = Field(ge=0.0, le=1.0)
    canonical_intent: CanonicalTradeIntent | None = None
    rejection_reasons: list[str] = Field(default_factory=list)
    reviewer_model: str
    deduplication: DeduplicationDecision | None = None
    omitted_stop_loss: OmittedStopLossDecision | None = None


class PositionSizingDecision(BaseModel):
    owner_id: OwnerId
    channel_id: str
    asset_group: AssetGroup
    strategy_tier: StrategyTier
    owner_weight: float = Field(ge=0.0)
    asset_group_weight: float = Field(ge=0.0)
    final_position_notional_usdt: Decimal = Field(ge=Decimal("0"))
    leverage: int = Field(ge=1, le=125)


class ConfidenceDecision(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    strategy_tier: StrategyTier
    source_confidence: float = Field(ge=0.0, le=1.0)
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    performance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    formula_version: str
    reasons: list[str] = Field(default_factory=list)


class PerformanceMetricsSnapshot(BaseModel):
    """Replayable strategy features derived from closed execution lifecycles."""

    owner_id: OwnerId
    channel_id: str
    asset_group: AssetGroup
    strategy_tier: StrategyTier
    sample_size: int = Field(ge=0)
    tp1_hit_rate: float = Field(ge=0.0, le=1.0)
    tp2_hit_rate: float = Field(ge=0.0, le=1.0)
    stop_loss_rate: float = Field(ge=0.0, le=1.0)
    cumulative_pnl_percentage: Decimal
    immediate_reversal_after_stop_rate: float = Field(ge=0.0, le=1.0)
    observed_at: datetime


class PairRiskLimit(BaseModel):
    """Owner/exchange/pair bounds applied after confidence-based sizing."""

    owner_id: OwnerId
    exchange_id: ExchangeId
    symbol: str = Field(min_length=1)
    maximum_cumulative_position_notional_usdt: Decimal = Field(gt=Decimal("0"))
    maximum_leverage: int = Field(ge=1, le=125)
    policy_version: str


class DeterministicRiskDecision(BaseModel):
    approved: bool
    owner_id: OwnerId
    exchange_id: ExchangeId
    symbol: str
    requested_position_notional_usdt: Decimal = Field(ge=Decimal("0"))
    existing_position_notional_usdt: Decimal = Field(ge=Decimal("0"))
    cumulative_position_notional_usdt: Decimal = Field(ge=Decimal("0"))
    requested_leverage: int = Field(ge=1, le=125)
    limits: PairRiskLimit
    reasons: list[str] = Field(default_factory=list)
    instant_price_deviation: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
    )
    maximum_instant_price_deviation: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
    )


class ClosedTradeOutcome(BaseModel):
    """Net closed-trade result used by deterministic pair blacklisting."""

    exchange_id: ExchangeId
    symbol: str = Field(min_length=1)
    closed_at: datetime
    realized_pnl_usdt: Decimal
    fees_usdt: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    funding_usdt: Decimal = Decimal("0")
    execution_cost_usdt: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    stopped_out: bool = False
    reversed_after_stop: bool = False

    @property
    def net_pnl_usdt(self) -> Decimal:
        return (
            self.realized_pnl_usdt
            - self.fees_usdt
            - self.funding_usdt
            - self.execution_cost_usdt
        )


class PairBlacklistDecision(BaseModel):
    exchange_id: ExchangeId
    symbol: str
    blacklisted: bool
    window_days: int = Field(ge=1)
    closed_trades: int = Field(ge=0)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    win_loss_ratio: Decimal | None = Field(default=None, ge=Decimal("0"))
    stop_reversal_rate: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )
    reasons: list[str] = Field(default_factory=list)
    policy_version: str
    computed_at: datetime


class PositionLifecycleEvent(BaseModel):
    """DynamoDB metadata for execution, P/L, and position-lifecycle replay."""

    event_id: str = Field(min_length=1)
    owner_id: OwnerId
    channel_id: str
    strategy_tier: StrategyTier
    exchange_id: ExchangeId
    symbol: str = Field(min_length=1)
    position_id: str = Field(min_length=1)
    trade_cursor_id: str | None = None
    event_type: Literal[
        "order_submitted",
        "order_filled",
        "take_profit_filled",
        "stop_loss_filled",
        "position_reduced",
        "position_closed",
    ]
    realized_pnl_usdt: Decimal | None = None
    occurred_at: datetime
    source_telegram_message_ids: list[str] = Field(default_factory=list)


class ApprovedExecutionRequest(BaseModel):
    intent: CanonicalTradeIntent
    sizing: PositionSizingDecision
    confidence: ConfidenceDecision
    lifecycle_strategy: PositionLifecycleStrategy
    risk_decisions: list[DeterministicRiskDecision] = Field(min_length=1)
    idempotency_key: str
    source_telegram_message_id: str | None = None
    parent_message_ids: list[str] = Field(default_factory=list)
    trade_cursor_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_execution_approval(self) -> Self:
        target_exchanges = set(self.intent.target_exchanges)
        risk_exchanges = {decision.exchange_id for decision in self.risk_decisions}
        if risk_exchanges != target_exchanges:
            raise ValueError("risk decisions must cover every target exchange exactly once")
        if len(self.risk_decisions) != len(risk_exchanges):
            raise ValueError("risk decisions must not contain duplicate exchanges")
        if any(not decision.approved for decision in self.risk_decisions):
            raise ValueError("an approved execution request cannot contain rejected risk")
        if any(
            decision.owner_id != self.intent.owner_id
            or decision.symbol.upper() != self.intent.symbol.upper()
            for decision in self.risk_decisions
        ):
            raise ValueError("risk decisions must match the intent owner and symbol")
        if self.intent.strategy_tier != self.confidence.strategy_tier:
            raise ValueError("intent and confidence strategy tiers must match")
        if self.intent.strategy_tier != self.sizing.strategy_tier:
            raise ValueError("intent and sizing strategy tiers must match")
        if self.intent.strategy_tier != self.lifecycle_strategy.strategy_tier:
            raise ValueError("intent and lifecycle strategy tiers must match")
        if (
            self.sizing.owner_weight != self.lifecycle_strategy.owner_weight
            or self.sizing.asset_group_weight
            != self.lifecycle_strategy.asset_group_weight
            or self.sizing.final_position_notional_usdt
            != self.lifecycle_strategy.position_notional_usdt
            or self.sizing.leverage != self.lifecycle_strategy.leverage
        ):
            raise ValueError("sizing must match the persisted lifecycle strategy")
        if (
            self.confidence.confidence != self.lifecycle_strategy.confidence
            or self.confidence.source_confidence
            != self.lifecycle_strategy.source_confidence
            or self.confidence.quality_score
            != self.lifecycle_strategy.quality_score
            or self.confidence.performance_score
            != self.lifecycle_strategy.performance_score
            or self.confidence.formula_version
            != self.lifecycle_strategy.formula_version
        ):
            raise ValueError("confidence must match the lifecycle strategy provenance")
        return self
