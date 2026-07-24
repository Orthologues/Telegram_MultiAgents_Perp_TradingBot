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
    TRADFI = "tradfi"
    MIXED = "mixed"


class StrategyTier(StrEnum):
    CONSERVATIVE = "conservative"
    INTERMEDIATE = "intermediate"
    RADICAL = "radical"


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
    BITMART = "bitmart"


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
    retrieval_cursor: str | None = None
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
        prompt_messages.append({"role": "current", **current})
        return prompt_messages


class TelegramAgentPollBatch(BaseModel):
    channel_id: str
    telegram_chat_id: str
    previous_cursor: str | None = None
    next_cursor: str | None = None
    messages: list[TelegramMessageEnvelope] = Field(default_factory=list)


class TelegramIngestionRecord(BaseModel):
    """Durable metadata record produced before downstream model delivery."""

    message: TelegramMessageEnvelope
    input_deduplication: DeduplicationDecision


class QwenSignalHypothesis(BaseModel):
    owner_id: OwnerId
    channel_id: str
    asset_group: AssetGroup
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
    """Typed Bitget/BitMart MCP input for Ministral validation."""

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


class ConfidenceDecision(BaseModel):
    approved: bool = True
    confidence: float = Field(ge=0.0, le=1.0)
    strategy_tier: StrategyTier
    reasons: list[str] = Field(default_factory=list)


class ApprovedExecutionRequest(BaseModel):
    intent: CanonicalTradeIntent
    sizing: PositionSizingDecision
    confidence: ConfidenceDecision
    idempotency_key: str
