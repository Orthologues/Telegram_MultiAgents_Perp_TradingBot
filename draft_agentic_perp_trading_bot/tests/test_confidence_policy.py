from datetime import datetime, timezone
from decimal import Decimal

import pytest

from agentic_perp_trading_bot.confidence_engine.policy import evaluate_confidence
from agentic_perp_trading_bot.risk_engine.policy import evaluate_deterministic_risk
from agentic_perp_trading_bot.schemas import (
    AssetGroup,
    ExchangeId,
    OwnerId,
    PairRiskLimit,
    PerformanceMetricsSnapshot,
    PositionSizingDecision,
    StrategyTier,
)


def _sizing(
    *,
    notional: str = "100",
    leverage: int = 3,
) -> PositionSizingDecision:
    return PositionSizingDecision(
        owner_id=OwnerId.OWNER_A_SHU_QIN,
        channel_id="owner_a_channel_a",
        asset_group=AssetGroup.MIXED,
        strategy_tier=StrategyTier.INTERMEDIATE,
        owner_weight=1.0,
        asset_group_weight=1.0,
        final_position_notional_usdt=Decimal(notional),
        leverage=leverage,
    )


def _limits(
    *,
    notional: str = "1000",
    leverage: int = 5,
) -> PairRiskLimit:
    return PairRiskLimit(
        owner_id=OwnerId.OWNER_A_SHU_QIN,
        exchange_id=ExchangeId.HYPERLIQUID,
        symbol="ALTUSDT",
        maximum_cumulative_position_notional_usdt=Decimal(notional),
        maximum_leverage=leverage,
        policy_version="test-v1",
    )


def test_confidence_exposes_all_five_strategy_tiers() -> None:
    decisions = [evaluate_confidence(score) for score in (0.1, 0.3, 0.5, 0.7, 0.9)]

    assert [decision.strategy_tier for decision in decisions] == list(StrategyTier)


def test_confidence_combines_ministral_quality_and_execution_metrics() -> None:
    performance = PerformanceMetricsSnapshot(
        owner_id=OwnerId.OWNER_A_SHU_QIN,
        channel_id="owner_a_channel_a",
        asset_group=AssetGroup.MIXED,
        strategy_tier=StrategyTier.INTERMEDIATE,
        sample_size=20,
        tp1_hit_rate=0.8,
        tp2_hit_rate=0.6,
        stop_loss_rate=0.2,
        cumulative_pnl_percentage=Decimal("12"),
        immediate_reversal_after_stop_rate=0.1,
        observed_at=datetime.now(timezone.utc),
    )

    decision = evaluate_confidence(
        0.7,
        quality_score=0.8,
        performance=performance,
    )

    assert decision.quality_score == 0.8
    assert decision.performance_score is not None
    assert decision.reasons == []


def test_blacklist_is_a_deterministic_risk_rejection() -> None:
    decision = evaluate_deterministic_risk(
        _sizing(),
        exchange_id=ExchangeId.HYPERLIQUID,
        symbol="ALTUSDT",
        limits=_limits(),
        pair_blacklisted=True,
    )

    assert decision.approved is False
    assert decision.reasons == ["trading_pair_blacklisted"]


def test_leverage_and_cumulative_notional_are_bounded_per_pair() -> None:
    decision = evaluate_deterministic_risk(
        _sizing(notional="150", leverage=4),
        exchange_id=ExchangeId.HYPERLIQUID,
        symbol="ALTUSDT",
        limits=_limits(notional="200", leverage=3),
        existing_position_notional_usdt=Decimal("75"),
    )

    assert decision.approved is False
    assert decision.reasons == [
        "requested_leverage_exceeds_pair_limit",
        "cumulative_position_notional_exceeds_pair_limit",
    ]


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
    limits = _limits().model_copy(update={"symbol": symbol})
    allowed = evaluate_deterministic_risk(
        _sizing(),
        exchange_id=ExchangeId.HYPERLIQUID,
        symbol=symbol,
        limits=limits,
        instant_order=True,
        asset_group=asset_group,
        reference_price=Decimal("100"),
        current_price=allowed_price,
    )
    rejected = evaluate_deterministic_risk(
        _sizing(),
        exchange_id=ExchangeId.HYPERLIQUID,
        symbol=symbol,
        limits=limits,
        instant_order=True,
        asset_group=asset_group,
        reference_price=Decimal("100"),
        current_price=rejected_price,
    )

    assert allowed.approved is True
    assert allowed.maximum_instant_price_deviation == threshold
    assert rejected.approved is False
    assert rejected.maximum_instant_price_deviation == threshold
