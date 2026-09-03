"""Draft performance and position-weight engine."""

from __future__ import annotations

from decimal import Decimal

from frameworkless_app.schemas import (
    FilterDecision,
    PositionSizingDecision,
    StrategyTier,
)

_TIER_NOTIONAL_MULTIPLIER = {
    StrategyTier.ULTRA_CONSERVATIVE: Decimal("0.25"),
    StrategyTier.CONSERVATIVE: Decimal("0.50"),
    StrategyTier.INTERMEDIATE: Decimal("1.00"),
    StrategyTier.RADICAL: Decimal("1.50"),
    StrategyTier.ULTRA_RADICAL: Decimal("2.00"),
}

_TIER_LEVERAGE = {
    StrategyTier.ULTRA_CONSERVATIVE: 1,
    StrategyTier.CONSERVATIVE: 2,
    StrategyTier.INTERMEDIATE: 3,
    StrategyTier.RADICAL: 4,
    StrategyTier.ULTRA_RADICAL: 5,
}


def compute_position_size(
    decision: FilterDecision,
    base_notional_usd: Decimal = Decimal("100"),
) -> PositionSizingDecision:
    """Compute dynamic notional from owner, asset-group, and quality weights."""
    if decision.canonical_intent is None:
        raise ValueError("Cannot size a rejected or non-canonical filter decision")

    intent = decision.canonical_intent
    owner_weight = Decimal("1.0")
    asset_group_weight = Decimal("1.0")
    strategy_tier = intent.strategy_tier
    final_notional = base_notional_usd * owner_weight * asset_group_weight
    final_notional *= Decimal(str(decision.quality_score))
    final_notional *= _TIER_NOTIONAL_MULTIPLIER[strategy_tier]

    return PositionSizingDecision(
        owner_id=intent.owner_id,
        channel_id=intent.channel_id,
        asset_group=intent.asset_group,
        strategy_tier=strategy_tier,
        owner_weight=float(owner_weight),
        asset_group_weight=float(asset_group_weight),
        final_position_notional_usd=final_notional,
        leverage=_TIER_LEVERAGE[strategy_tier],
    )
