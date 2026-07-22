"""Confidence mapping and the two allowed hard rejection checks."""

from __future__ import annotations

from decimal import Decimal

from agentic_perp_trading_bot.schemas import ConfidenceDecision, StrategyTier


def evaluate_confidence(
    source_confidence: float,
    *,
    pair_blacklisted: bool = False,
    instant_order: bool = False,
    reference_price: Decimal | None = None,
    current_price: Decimal | None = None,
    maximum_instant_price_deviation: Decimal = Decimal("0.02"),
) -> ConfidenceDecision:
    """Map confidence to a tier and apply only the two explicit hard rejections."""
    confidence = min(max(float(source_confidence), 0.0), 1.0)
    strategy_tier = _strategy_tier_for(confidence)
    reasons: list[str] = []

    if pair_blacklisted:
        reasons.append("trading_pair_blacklisted")

    if instant_order and reference_price is not None and current_price is not None:
        if reference_price <= 0 or current_price <= 0:
            reasons.append("invalid_instant_order_price")
        else:
            deviation = abs(current_price - reference_price) / reference_price
            if deviation > maximum_instant_price_deviation:
                reasons.append("instant_order_price_too_far_from_reference")

    return ConfidenceDecision(
        approved=not reasons,
        confidence=confidence,
        strategy_tier=strategy_tier,
        reasons=reasons,
    )


def _strategy_tier_for(confidence: float) -> StrategyTier:
    if confidence < 0.5:
        return StrategyTier.CONSERVATIVE
    if confidence < 0.8:
        return StrategyTier.INTERMEDIATE
    return StrategyTier.RADICAL
