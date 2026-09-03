"""Deterministic omitted stop-loss policy owned by the Ministral boundary."""

from __future__ import annotations

from decimal import Decimal

from frameworkless_app.schemas import (
    IndicatorTimeframe,
    IntentType,
    MarketAnalysisSnapshot,
    MarketLiquidityTier,
    OmittedStopLossDecision,
    QwenSignalHypothesis,
    TechnicalIndicatorSnapshot,
    TradingPairType,
)

MINIMUM_DISTANCE = Decimal("0.012")
MAXIMUM_DISTANCE = Decimal("0.08")
POLICY_VERSION = "pair-type-volume-multitimeframe-indicators-v3"

_LARGE_CAP_MINIMUM = Decimal("10000000000")
_LARGE_VOLUME_MINIMUM = Decimal("500000000")
_MID_CAP_MINIMUM = Decimal("1000000000")
_MID_VOLUME_MINIMUM = Decimal("50000000")

_PAIR_TYPE_DISTANCE_BANDS = {
    TradingPairType.TRADFI: (MINIMUM_DISTANCE, Decimal("0.035")),
    TradingPairType.MAINSTREAM_COIN: (Decimal("0.015"), Decimal("0.05")),
    TradingPairType.ALTCOIN: (Decimal("0.025"), MAXIMUM_DISTANCE),
}
_INDICATOR_WEIGHTS = {
    "ema": Decimal("0.12"),
    "macd": Decimal("0.12"),
    "kdj": Decimal("0.10"),
    "rsi": Decimal("0.10"),
    "bollinger": Decimal("0.18"),
    "atr": Decimal("0.23"),
    "realized_volatility": Decimal("0.15"),
}
_TIMEFRAME_WEIGHTS = {
    IndicatorTimeframe.FIVE_MINUTES: Decimal("0.10"),
    IndicatorTimeframe.FIFTEEN_MINUTES: Decimal("0.20"),
    IndicatorTimeframe.ONE_HOUR: Decimal("0.30"),
    IndicatorTimeframe.FOUR_HOURS: Decimal("0.40"),
}


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
        volume_score = self._volume_score(market.quote_volume_24h_usd)
        technical_score, components = self._technical_score(market, direction)
        placement_score = (
            Decimal("0.35") * volume_score
            + Decimal("0.65") * technical_score
        )
        lower, upper = _PAIR_TYPE_DISTANCE_BANDS[market.trading_pair_type]
        distance = lower + (upper - lower) * placement_score
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
            trading_pair_type=market.trading_pair_type,
            volume_score=volume_score,
            technical_score=technical_score,
            volatility_score=technical_score,
            component_scores={
                **components,
                "volume": volume_score,
                "placement": placement_score,
            },
            market_snapshot=market,
            policy_version=POLICY_VERSION,
            evidence=[
                "mcp_market_cap_usd",
                "mcp_quote_volume_24h_usd",
                "mcp_trading_pair_type",
                "mcp_ema_macd_kdj_rsi_5m_15m_1h_4h",
                "mcp_bollinger_atr_realized_volatility_5m_15m_1h_4h",
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
    def _volume_score(quote_volume_24h_usd: Decimal) -> Decimal:
        thresholds = (
            (Decimal("500000000"), Decimal("0")),
            (Decimal("100000000"), Decimal("0.25")),
            (Decimal("25000000"), Decimal("0.50")),
            (Decimal("5000000"), Decimal("0.75")),
            (Decimal("0"), Decimal("1")),
        )
        for floor, score in thresholds:
            if quote_volume_24h_usd >= floor:
                return score
        raise AssertionError("volume score thresholds must cover non-negative values")

    @staticmethod
    def _technical_score(
        market: MarketAnalysisSnapshot,
        direction: str,
    ) -> tuple[Decimal, dict[str, Decimal]]:
        component_totals = {name: Decimal("0") for name in _INDICATOR_WEIGHTS}
        for timeframe, timeframe_weight in _TIMEFRAME_WEIGHTS.items():
            scores = MinistralStopLossPolicy._timeframe_indicator_scores(
                market.indicators[timeframe],
                market.current_price,
                direction,
            )
            for name, score in scores.items():
                component_totals[name] += timeframe_weight * score
        technical_score = sum(
            _INDICATOR_WEIGHTS[name] * component_totals[name]
            for name in _INDICATOR_WEIGHTS
        )
        return _unit_interval(technical_score), component_totals

    @staticmethod
    def _timeframe_indicator_scores(
        indicators: TechnicalIndicatorSnapshot,
        current_price: Decimal,
        direction: str,
    ) -> dict[str, Decimal]:
        ema_gap = abs(indicators.ema_fast - indicators.ema_slow) / current_price
        ema_opposes = (
            direction == "long" and indicators.ema_fast < indicators.ema_slow
        ) or (
            direction == "short" and indicators.ema_fast > indicators.ema_slow
        )
        ema_score = _unit_interval(ema_gap / Decimal("0.05"))
        if not ema_opposes:
            ema_score *= Decimal("0.5")

        macd_gap = abs(indicators.macd - indicators.macd_signal) / current_price
        macd_opposes = (
            direction == "long" and indicators.macd < indicators.macd_signal
        ) or (
            direction == "short" and indicators.macd > indicators.macd_signal
        )
        macd_score = _unit_interval(macd_gap / Decimal("0.03"))
        if not macd_opposes:
            macd_score *= Decimal("0.5")

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
        rsi_score = _unit_interval(
            abs(indicators.rsi - Decimal("50")) / Decimal("50")
        )
        realized_volatility_score = _unit_interval(
            indicators.realized_volatility_fraction / Decimal("0.10")
        )
        return {
            "ema": ema_score,
            "macd": macd_score,
            "kdj": kdj_score,
            "rsi": rsi_score,
            "bollinger": bollinger_score,
            "atr": atr_score,
            "realized_volatility": realized_volatility_score,
        }


def _unit_interval(value: Decimal) -> Decimal:
    return min(max(value, Decimal("0")), Decimal("1"))
