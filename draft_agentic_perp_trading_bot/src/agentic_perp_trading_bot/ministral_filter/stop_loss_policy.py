"""Deterministic omitted stop-loss policy owned by the Ministral boundary."""

from __future__ import annotations

from decimal import Decimal

from agentic_perp_trading_bot.schemas import (
    IndicatorTimeframe,
    IntentType,
    MarketAnalysisSnapshot,
    MarketLiquidityTier,
    OmittedStopLossDecision,
    QwenSignalHypothesis,
    TechnicalIndicatorSnapshot,
)

MINIMUM_DISTANCE = Decimal("0.0125")
MAXIMUM_DISTANCE = Decimal("0.075")
POLICY_VERSION = "market-liquidity-multitimeframe-volatility-v2"

_LARGE_CAP_MINIMUM = Decimal("10000000000")
_LARGE_VOLUME_MINIMUM = Decimal("500000000")
_MID_CAP_MINIMUM = Decimal("1000000000")
_MID_VOLUME_MINIMUM = Decimal("50000000")

_DISTANCE_BANDS = {
    MarketLiquidityTier.LARGE: (MINIMUM_DISTANCE, Decimal("0.025")),
    MarketLiquidityTier.MID: (Decimal("0.03"), Decimal("0.05")),
    MarketLiquidityTier.SMALL: (Decimal("0.06"), MAXIMUM_DISTANCE),
}
_BOLLINGER_WEIGHT = Decimal("0.50")
_ATR_WEIGHT = Decimal("0.30")
_KDJ_WEIGHT = Decimal("0.20")
_REQUIRED_TIMEFRAMES = tuple(IndicatorTimeframe)


class MinistralStopLossPolicy:
    """Derive an auditable stop-loss without QWEN or free-form model output."""

    def derive(
        self,
        hypothesis: QwenSignalHypothesis,
        market: MarketAnalysisSnapshot,
    ) -> OmittedStopLossDecision | None:
        if hypothesis.stop_loss is not None:
            return None
        if hypothesis.intent_type not in {
            IntentType.NEW_ORDER,
            IntentType.ADD_POSITION,
        }:
            return None
        if hypothesis.symbol is None or hypothesis.symbol.upper() != market.symbol.upper():
            raise ValueError("market snapshot symbol does not match QWEN hypothesis")

        direction = (hypothesis.direction or "").lower()
        if direction not in {"long", "short"}:
            raise ValueError("omitted stop-loss requires a long or short direction")

        liquidity_tier = self._liquidity_tier(market)
        volatility_score = self._volatility_score(market)
        lower, upper = _DISTANCE_BANDS[liquidity_tier]
        distance = lower + (upper - lower) * volatility_score
        distance = min(max(distance, MINIMUM_DISTANCE), MAXIMUM_DISTANCE)
        reference_price = self._entry_reference_price(hypothesis)

        if direction == "long":
            stop_loss = reference_price * (Decimal("1") - distance)
        else:
            stop_loss = reference_price * (Decimal("1") + distance)

        return OmittedStopLossDecision(
            stop_loss=stop_loss,
            distance_fraction=distance,
            liquidity_tier=liquidity_tier,
            volatility_score=volatility_score,
            market_snapshot=market,
            policy_version=POLICY_VERSION,
            evidence=[
                "mcp_market_cap_usd",
                "mcp_quote_volume_24h_usd",
                "mcp_kdj_5m_15m_1h_4h",
                "mcp_bollinger_bands_5m_15m_1h_4h",
                "mcp_average_true_range_5m_15m_1h_4h",
            ],
        )

    @staticmethod
    def _entry_reference_price(hypothesis: QwenSignalHypothesis) -> Decimal:
        if not hypothesis.entries:
            raise ValueError("omitted stop-loss requires at least one entry price")
        if len(hypothesis.entries) == 1:
            return hypothesis.entries[0]
        return (hypothesis.entries[0] + hypothesis.entries[1]) / Decimal("2")

    @staticmethod
    def _liquidity_tier(market: MarketAnalysisSnapshot) -> MarketLiquidityTier:
        if (
            market.market_cap_usd >= _LARGE_CAP_MINIMUM
            and market.quote_volume_24h_usd >= _LARGE_VOLUME_MINIMUM
        ):
            return MarketLiquidityTier.LARGE
        if (
            market.market_cap_usd >= _MID_CAP_MINIMUM
            and market.quote_volume_24h_usd >= _MID_VOLUME_MINIMUM
        ):
            return MarketLiquidityTier.MID
        return MarketLiquidityTier.SMALL

    @staticmethod
    def _volatility_score(market: MarketAnalysisSnapshot) -> Decimal:
        timeframe_scores = [
            MinistralStopLossPolicy._timeframe_volatility_score(
                market.indicators[timeframe],
                market.current_price,
            )
            for timeframe in _REQUIRED_TIMEFRAMES
        ]
        return sum(timeframe_scores, Decimal("0")) / Decimal(
            len(_REQUIRED_TIMEFRAMES)
        )

    @staticmethod
    def _timeframe_volatility_score(
        indicators: TechnicalIndicatorSnapshot,
        current_price: Decimal,
    ) -> Decimal:
        bollinger_bandwidth = (
            indicators.bollinger_upper - indicators.bollinger_lower
        ) / indicators.bollinger_middle
        bollinger_score = _unit_interval(
            bollinger_bandwidth / Decimal("0.20")
        )

        atr_fraction = indicators.average_true_range / current_price
        atr_score = _unit_interval(atr_fraction / Decimal("0.10"))

        kdj_values = (indicators.kdj_k, indicators.kdj_d, indicators.kdj_j)
        kdj_dispersion = (max(kdj_values) - min(kdj_values)) / Decimal("100")
        kdj_score = _unit_interval(kdj_dispersion)
        return (
            _BOLLINGER_WEIGHT * bollinger_score
            + _ATR_WEIGHT * atr_score
            + _KDJ_WEIGHT * kdj_score
        )


def _unit_interval(value: Decimal) -> Decimal:
    return min(max(value, Decimal("0")), Decimal("1"))
