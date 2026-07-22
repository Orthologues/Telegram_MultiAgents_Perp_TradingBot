from decimal import Decimal

from agentic_perp_trading_bot.confidence_engine.policy import evaluate_confidence
from agentic_perp_trading_bot.schemas import StrategyTier


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
