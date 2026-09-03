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


# prices are each at most twice the Qwen3 VL 235B A22B baseline.
class BedrockModelId(StrEnum):
    """Bedrock model IDs currently selected by the CrewAI scaffold."""

    QWEN3_VL_235B_A22B = "qwen.qwen3-vl-235b-a22b"
    MINISTRAL_3_8B_INSTRUCT = "mistral.ministral-3-8b-instruct"
    DEEPSEEK_V3_2 = "deepseek.v3.2"
    GLM_4_7 = "zai.glm-4.7"
    GLM_4_7_FLASH = "zai.glm-4.7-flash"
    GLM_5 = "zai.glm-5"
    LLAMA_4_MAVERICK_17B_INSTRUCT = "meta.llama4-maverick-17b-instruct-v1:0"
    LLAMA_4_SCOUT_17B_INSTRUCT = "meta.llama4-scout-17b-instruct-v1:0"


ACCEPTABLE_ALTERNATIVE_OWNER_MODEL_IDS: frozenset[BedrockModelId] = frozenset(
    {
        BedrockModelId.DEEPSEEK_V3_2,
        BedrockModelId.GLM_4_7,
        BedrockModelId.GLM_4_7_FLASH,
        BedrockModelId.GLM_5,
        BedrockModelId.LLAMA_4_MAVERICK_17B_INSTRUCT,
        BedrockModelId.LLAMA_4_SCOUT_17B_INSTRUCT,
    }
)


__all__ = [
    "ACCEPTABLE_ALTERNATIVE_OWNER_MODEL_IDS",
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
