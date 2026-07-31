import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from agentic_perp_trading_bot.ministral_filter.filter_agent import (
    MinistralFilterAgent,
)
from agentic_perp_trading_bot.ministral_filter.stop_loss_policy import (
    MinistralStopLossPolicy,
)
from agentic_perp_trading_bot.orchestrator import process_message
from agentic_perp_trading_bot.schemas import (
    AssetGroup,
    CanonicalTradeIntent,
    ExchangeId,
    FilterDecision,
    IndicatorTimeframe,
    IntentType,
    MarketAnalysisSnapshot,
    MarketLiquidityTier,
    OwnerId,
    QwenSignalHypothesis,
    SettlementAsset,
    StrategyTier,
    TechnicalIndicatorSnapshot,
    TradeAction,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradingPairType,
)


def _hypothesis(
    *,
    direction: str = "long",
    stop_loss: Decimal | None = None,
    entries: list[Decimal] | None = None,
) -> QwenSignalHypothesis:
    return QwenSignalHypothesis(
        owner_id=OwnerId.OWNER_B_LAO_TU,
        channel_id="owner_b_channel",
        asset_group=AssetGroup.ALTS,
        strategy_tier=StrategyTier.INTERMEDIATE,
        intent_type=IntentType.NEW_ORDER,
        symbol="ALTUSDT",
        direction=direction,
        entries=entries if entries is not None else [Decimal("100")],
        stop_loss=stop_loss,
        confidence=Decimal("0.7"),
    )


def _market(
    *,
    market_cap: str,
    volume: str,
    upper: str = "110",
    middle: str = "100",
    lower: str = "90",
    average_true_range: str = "4",
    pair_type: TradingPairType = TradingPairType.MAINSTREAM_COIN,
    ema_fast: str = "100",
    ema_slow: str = "100",
    macd: str = "0",
    macd_signal: str = "0",
    rsi: str = "50",
    realized_volatility: str = "0.02",
) -> MarketAnalysisSnapshot:
    indicators = {
        timeframe: TechnicalIndicatorSnapshot(
            ema_fast=Decimal(ema_fast),
            ema_slow=Decimal(ema_slow),
            macd=Decimal(macd),
            macd_signal=Decimal(macd_signal),
            kdj_k=Decimal("60"),
            kdj_d=Decimal("50"),
            kdj_j=Decimal("80"),
            rsi=Decimal(rsi),
            bollinger_upper=Decimal(upper),
            bollinger_middle=Decimal(middle),
            bollinger_lower=Decimal(lower),
            average_true_range=Decimal(average_true_range),
            realized_volatility_fraction=Decimal(realized_volatility),
        )
        for timeframe in IndicatorTimeframe
    }
    return MarketAnalysisSnapshot(
        exchange_id=ExchangeId.HYPERLIQUID,
        settlement_asset=SettlementAsset.USDC,
        symbol="ALTUSDT",
        trading_pair_type=pair_type,
        current_price=Decimal("100"),
        market_cap_usd=Decimal(market_cap),
        quote_volume_24h_usd=Decimal(volume),
        indicators=indicators,
        observed_at=datetime.now(timezone.utc),
    )


def test_large_liquid_pair_stays_near_minimum_stop_distance() -> None:
    decision = MinistralStopLossPolicy().derive(
        _hypothesis(),
        _market(market_cap="20000000000", volume="1000000000", upper="102", lower="98"),
    )

    assert decision is not None
    assert decision.liquidity_tier == MarketLiquidityTier.LARGE
    assert Decimal("0.015") <= decision.distance_fraction <= Decimal("0.05")
    assert decision.stop_loss < Decimal("100")


def test_small_volatile_short_stays_near_maximum_stop_distance() -> None:
    decision = MinistralStopLossPolicy().derive(
        _hypothesis(direction="short"),
        _market(
            market_cap="50000000",
            volume="1000000",
            pair_type=TradingPairType.ALTCOIN,
            upper="120",
            lower="80",
            average_true_range="10",
            ema_fast="110",
            ema_slow="90",
            macd="10",
            macd_signal="0",
            rsi="100",
            realized_volatility="0.10",
        ),
    )

    assert decision is not None
    assert decision.liquidity_tier == MarketLiquidityTier.SMALL
    assert Decimal("0.06") <= decision.distance_fraction <= Decimal("0.08")
    assert decision.stop_loss > Decimal("100")


def test_atr_across_all_timeframes_increases_the_stop_distance() -> None:
    low_atr = MinistralStopLossPolicy().derive(
        _hypothesis(),
        _market(
            market_cap="1000000000",
            volume="50000000",
            average_true_range="1",
        ),
    )
    high_atr = MinistralStopLossPolicy().derive(
        _hypothesis(),
        _market(
            market_cap="1000000000",
            volume="50000000",
            average_true_range="10",
        ),
    )

    assert low_atr is not None
    assert high_atr is not None
    assert high_atr.distance_fraction > low_atr.distance_fraction


def test_single_entry_stop_loss_is_bounded_from_entry1() -> None:
    entry1 = Decimal("120")
    decision = MinistralStopLossPolicy().derive(
        _hypothesis(entries=[entry1]),
        _market(market_cap="50000000", volume="1000000"),
    )

    assert decision is not None
    assert decision.stop_loss == entry1 * (
        Decimal("1") - decision.distance_fraction
    )
    assert (entry1 - decision.stop_loss) / entry1 <= Decimal("0.08")


def test_two_entries_stop_loss_is_bounded_from_average_entry_price() -> None:
    entry1 = Decimal("120")
    entry2 = Decimal("110")
    reference_price = (entry1 + entry2) / Decimal("2")
    decision = MinistralStopLossPolicy().derive(
        _hypothesis(entries=[entry1, entry2]),
        _market(market_cap="50000000", volume="1000000"),
    )

    assert decision is not None
    assert decision.stop_loss == reference_price * (
        Decimal("1") - decision.distance_fraction
    )
    assert (reference_price - decision.stop_loss) / reference_price <= Decimal(
        "0.08"
    )


def test_omitted_stop_loss_requires_an_entry_reference_price() -> None:
    with pytest.raises(ValueError, match="at least one entry"):
        MinistralStopLossPolicy().derive(
            _hypothesis(entries=[]),
            _market(market_cap="50000000", volume="1000000"),
        )


def test_market_snapshot_requires_every_indicator_timeframe() -> None:
    market_data = _market(
        market_cap="50000000",
        volume="1000000",
    ).model_dump()
    del market_data["indicators"][IndicatorTimeframe.FIVE_MINUTES]

    with pytest.raises(ValueError, match="exactly 5m, 15m, 1h, and 4h"):
        MarketAnalysisSnapshot.model_validate(market_data)


@pytest.mark.parametrize("timeframe", list(IndicatorTimeframe))
@pytest.mark.parametrize(
    "indicator_family",
    ["ema", "macd", "kdj", "rsi", "bollinger", "atr", "realized_volatility"],
)
def test_every_indicator_family_contributes_from_every_timeframe(
    timeframe: IndicatorTimeframe,
    indicator_family: str,
) -> None:
    baseline_market = _market(
        market_cap="1000000000",
        volume="50000000",
        upper="101",
        lower="99",
        average_true_range="1",
    )
    elevated_data = baseline_market.model_dump()
    elevated_indicator = elevated_data["indicators"][timeframe]
    if indicator_family == "ema":
        elevated_indicator["ema_fast"] = Decimal("90")
        elevated_indicator["ema_slow"] = Decimal("110")
    elif indicator_family == "macd":
        elevated_indicator["macd"] = Decimal("-10")
        elevated_indicator["macd_signal"] = Decimal("0")
    elif indicator_family == "kdj":
        elevated_indicator["kdj_j"] = Decimal("150")
    elif indicator_family == "rsi":
        elevated_indicator["rsi"] = Decimal("100")
    elif indicator_family == "bollinger":
        elevated_indicator["bollinger_upper"] = Decimal("110")
        elevated_indicator["bollinger_lower"] = Decimal("90")
    elif indicator_family == "atr":
        elevated_indicator["average_true_range"] = Decimal("10")
    else:
        elevated_indicator["realized_volatility_fraction"] = Decimal("0.10")

    baseline = MinistralStopLossPolicy().derive(_hypothesis(), baseline_market)
    elevated = MinistralStopLossPolicy().derive(
        _hypothesis(),
        MarketAnalysisSnapshot.model_validate(elevated_data),
    )

    assert baseline is not None
    assert elevated is not None
    assert elevated.distance_fraction > baseline.distance_fraction


def test_explicit_qwen_stop_loss_is_not_replaced() -> None:
    decision = MinistralStopLossPolicy().derive(
        _hypothesis(stop_loss=Decimal("95")),
        _market(market_cap="50000000", volume="1000000"),
    )

    assert decision is None


def test_market_snapshot_must_match_signal_symbol() -> None:
    market = _market(market_cap="50000000", volume="1000000").model_copy(
        update={"symbol": "OTHERUSDT"}
    )

    with pytest.raises(ValueError, match="symbol"):
        MinistralStopLossPolicy().derive(_hypothesis(), market)


def test_ministral_review_records_deterministic_stop_loss() -> None:
    message = TelegramMessageEnvelope(
        owner_id=OwnerId.OWNER_B_LAO_TU,
        channel_id="owner_b_channel",
        asset_group=AssetGroup.ALTS,
        telegram_message_id="123",
        received_at=datetime.now(timezone.utc),
    )
    decision = asyncio.run(
        MinistralFilterAgent("ministral-3-8b").review(
            _hypothesis(),
            TelegramPromptContext.from_message(message),
            _market(market_cap="50000000", volume="1000000"),
        )
    )

    assert decision.omitted_stop_loss is not None
    assert decision.omitted_stop_loss.reasoning_budget_ms == 1000


def test_orchestrator_copies_derived_stop_into_approved_intent() -> None:
    message = TelegramMessageEnvelope(
        owner_id=OwnerId.OWNER_B_LAO_TU,
        channel_id="owner_b_channel",
        asset_group=AssetGroup.ALTS,
        telegram_message_id="123",
        received_at=datetime.now(timezone.utc),
        dedup_key="message-123",
    )
    hypothesis = _hypothesis()
    market = _market(market_cap="50000000", volume="1000000")
    omitted_stop = MinistralStopLossPolicy().derive(hypothesis, market)
    assert omitted_stop is not None

    class QwenStub:
        async def infer_signal(self, message, prompt_context=None):
            return hypothesis

    class MinistralStub:
        async def review(self, hypothesis, prompt_context, market_snapshot=None):
            return FilterDecision(
                status="approved",
                quality_score=0.8,
                canonical_intent=CanonicalTradeIntent(
                    owner_id=OwnerId.OWNER_B_LAO_TU,
                    channel_id="owner_b_channel",
                    asset_group=AssetGroup.ALTS,
                    strategy_tier=StrategyTier.INTERMEDIATE,
                    symbol="ALTUSDT",
                    action=TradeAction.OPEN_LONG,
                    order_type="limit",
                    entries=[Decimal("100")],
                    target_exchanges=[ExchangeId.HYPERLIQUID],
                ),
                reviewer_model="ministral-3-8b",
                omitted_stop_loss=omitted_stop,
            )

    request = asyncio.run(
        process_message(
            message,
            QwenStub(),
            MinistralStub(),
            market_snapshot=market,
        )
    )

    assert request is not None
    assert request.intent.stop_loss == omitted_stop.stop_loss
