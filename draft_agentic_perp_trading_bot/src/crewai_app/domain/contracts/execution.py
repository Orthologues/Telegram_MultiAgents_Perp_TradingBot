"""Market-snapshot, model, and guarded-execution contracts."""

from enum import StrEnum

from frameworkless_app.schemas import (
    ApprovedExecutionRequest,
    DeterministicRiskDecision,
    ExchangeId,
    ExchangeNetwork,
    IndicatorTimeframe,
    MarketAnalysisSnapshot,
    MarketLiquidityTier,
    OmittedStopLossDecision,
    PairBlacklistDecision,
    PairRiskLimit,
    SettlementAsset,
    TechnicalIndicatorSnapshot,
    TradingPairType,
    settlement_asset_for_exchange,
)


class BedrockModelId(StrEnum):
    """Bedrock model IDs currently selected by the CrewAI scaffold."""

    QWEN3_VL_235B_A22B = "qwen.qwen3-vl-235b-a22b"
    MINISTRAL_3_8B_INSTRUCT = "mistral.ministral-3-8b-instruct"


__all__ = [
    "ApprovedExecutionRequest",
    "BedrockModelId",
    "DeterministicRiskDecision",
    "ExchangeId",
    "ExchangeNetwork",
    "IndicatorTimeframe",
    "MarketAnalysisSnapshot",
    "MarketLiquidityTier",
    "OmittedStopLossDecision",
    "PairBlacklistDecision",
    "PairRiskLimit",
    "SettlementAsset",
    "TechnicalIndicatorSnapshot",
    "TradingPairType",
    "settlement_asset_for_exchange",
]
