from decimal import Decimal

import pytest

from agentic_perp_trading_bot.confidence_engine.policy import evaluate_confidence
from agentic_perp_trading_bot.schemas import AssetGroup, StrategyTier


def test_confidence_selects_conservative_tier_for_lower_scores() -> None:
    decision = evaluate_confidence(0.2)

    assert decision.approved is True
    assert decision.strategy_tier == StrategyTier.CONSERVATIVE


def test_blacklisted_pair_is_the_only_pair_rejection() -> None:
    decision = evaluate_confidence(0.8, pair_blacklisted=True)

    assert decision.approved is False
    assert decision.reasons == ["trading_pair_blacklisted"]


def test_market_order_is_rejected_when_current_price_is_too_far_from_reference() -> None:
    decision = evaluate_confidence(
        0.8,
        instant_order=True,
        reference_price=Decimal("100"),
        current_price=Decimal("103"),
    )

    assert decision.approved is False
    assert decision.reasons == ["instant_order_price_too_far_from_reference"]


@pytest.mark.parametrize("symbol", ["BNBUSDT", "ETH-USDT", "SOL/USDT"])
def test_major_crypto_uses_point_two_five_percent_threshold(symbol: str) -> None:
    decision = evaluate_confidence(
        0.8,
        instant_order=True,
        symbol=symbol,
        reference_price=Decimal("100"),
        current_price=Decimal("100.251"),
    )

    assert decision.approved is False
    assert decision.maximum_instant_price_deviation == Decimal("0.0025")


def test_tradfi_perpetual_uses_point_two_five_percent_threshold() -> None:
    decision = evaluate_confidence(
        0.8,
        instant_order=True,
        symbol="XAUUSDT",
        asset_group=AssetGroup.TRADFI,
        reference_price=Decimal("100"),
        current_price=Decimal("100.251"),
    )

    assert decision.approved is False
    assert decision.maximum_instant_price_deviation == Decimal("0.0025")


def test_explicit_tradfi_metadata_overrides_a_mixed_channel_group() -> None:
    decision = evaluate_confidence(
        0.8,
        instant_order=True,
        symbol="XAUUSDT",
        asset_group=AssetGroup.MIXED,
        tradfi_perpetual_pair=True,
        reference_price=Decimal("100"),
        current_price=Decimal("100.251"),
    )

    assert decision.approved is False
    assert decision.maximum_instant_price_deviation == Decimal("0.0025")


@pytest.mark.parametrize(
    ("symbol", "asset_group", "allowed_price", "rejected_price", "threshold"),
    [
        (
            "BTCUSDT",
            AssetGroup.BTC_ETH,
            Decimal("100.125"),
            Decimal("100.126"),
            Decimal("0.00125"),
        ),
        (
            "ETHUSDT",
            AssetGroup.BTC_ETH,
            Decimal("100.25"),
            Decimal("100.251"),
            Decimal("0.0025"),
        ),
        (
            "ALTUSDT",
            AssetGroup.ALTS,
            Decimal("100.5"),
            Decimal("100.501"),
            Decimal("0.005"),
        ),
    ],
)
def test_instant_price_deviation_boundaries_are_strict(
    symbol: str,
    asset_group: AssetGroup,
    allowed_price: Decimal,
    rejected_price: Decimal,
    threshold: Decimal,
) -> None:
    allowed = evaluate_confidence(
        0.8,
        instant_order=True,
        symbol=symbol,
        asset_group=asset_group,
        reference_price=Decimal("100"),
        current_price=allowed_price,
    )
    rejected = evaluate_confidence(
        0.8,
        instant_order=True,
        symbol=symbol,
        asset_group=asset_group,
        reference_price=Decimal("100"),
        current_price=rejected_price,
    )

    assert allowed.approved is True
    assert allowed.maximum_instant_price_deviation == threshold
    assert rejected.approved is False
    assert rejected.maximum_instant_price_deviation == threshold
