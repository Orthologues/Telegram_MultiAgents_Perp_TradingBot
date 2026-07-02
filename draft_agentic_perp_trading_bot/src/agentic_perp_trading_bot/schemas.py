"""Shared schemas for the draft multi-agent perpetual futures trading bot."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


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


class TelegramMessageEnvelope(BaseModel):
    owner_id: OwnerId
    channel_id: str
    asset_group: AssetGroup
    telegram_message_id: str
    received_at: datetime
    raw_text: str | None = None
    media_s3_uri: str | None = None
    language_hint: str = "zh"
    strategy_tier_hint: StrategyTier | None = None


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


class FilterDecision(BaseModel):
    status: str
    quality_score: float = Field(ge=0.0, le=1.0)
    canonical_intent: CanonicalTradeIntent | None = None
    rejection_reasons: list[str] = Field(default_factory=list)
    reviewer_model: str


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
