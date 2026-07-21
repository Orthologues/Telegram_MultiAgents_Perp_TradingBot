"""Shared schemas for the draft multi-agent perpetual futures trading bot."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator


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


class ExchangeId(StrEnum):
    BITGET = "bitget"
    BITMART = "bitmart"


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


class TelegramAgentPollBatch(BaseModel):
    channel_id: str
    telegram_chat_id: str
    previous_cursor: str | None = None
    next_cursor: str | None = None
    messages: list[TelegramMessageEnvelope] = Field(default_factory=list)


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


class PositionSizingDecision(BaseModel):
    owner_id: OwnerId
    channel_id: str
    asset_group: AssetGroup
    strategy_tier: StrategyTier
    owner_weight: float = Field(ge=0.0)
    asset_group_weight: float = Field(ge=0.0)
    final_position_notional_usdt: Decimal = Field(ge=Decimal("0"))


class RiskDecision(BaseModel):
    approved: bool
    max_position_notional_usdt: Decimal
    max_leverage: int
    allowed_exchanges: list[ExchangeId]
    reasons: list[str] = Field(default_factory=list)


class ApprovedExecutionRequest(BaseModel):
    intent: CanonicalTradeIntent
    sizing: PositionSizingDecision
    risk: RiskDecision
    idempotency_key: str
