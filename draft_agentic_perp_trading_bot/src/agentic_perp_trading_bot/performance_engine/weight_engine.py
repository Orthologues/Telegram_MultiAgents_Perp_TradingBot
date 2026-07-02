"""Draft performance and position-weight engine."""

from __future__ import annotations

from decimal import Decimal

from agentic_perp_trading_bot.schemas import (
    FilterDecision,
    PositionSizingDecision,
    StrategyTier,
)


def compute_position_size(
    decision: FilterDecision,
    base_notional_usdt: Decimal = Decimal("100"),
) -> PositionSizingDecision:
    """Compute dynamic notional from owner, asset-group, and quality weights."""
    if decision.canonical_intent is None:
        raise ValueError("Cannot size a rejected or non-canonical filter decision")

    intent = decision.canonical_intent
    owner_weight = Decimal("1.0")
    asset_group_weight = Decimal("1.0")
    final_notional = base_notional_usdt * owner_weight * asset_group_weight
    final_notional *= Decimal(str(decision.quality_score))

    return PositionSizingDecision(
        owner_id=intent.owner_id,
        channel_id=intent.channel_id,
        asset_group=intent.asset_group,
        strategy_tier=intent.strategy_tier or StrategyTier.INTERMEDIATE,
        owner_weight=float(owner_weight),
        asset_group_weight=float(asset_group_weight),
        final_position_notional_usdt=final_notional,
    )
