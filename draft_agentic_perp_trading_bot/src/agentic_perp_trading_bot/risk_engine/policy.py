"""Draft deterministic risk checks before order execution."""

from __future__ import annotations

from decimal import Decimal

from agentic_perp_trading_bot.schemas import ExchangeId, PositionSizingDecision, RiskDecision


def evaluate_risk(
    sizing: PositionSizingDecision,
    max_notional_usdt: Decimal = Decimal("250"),
    max_leverage: int = 3,
) -> RiskDecision:
    """Apply hard risk limits to the performance-weighted position size."""
    approved = sizing.final_position_notional_usdt <= max_notional_usdt
    reasons = []
    if not approved:
        reasons.append("position_notional_exceeds_limit")

    return RiskDecision(
        approved=approved,
        max_position_notional_usdt=max_notional_usdt,
        max_leverage=max_leverage,
        allowed_exchanges=[ExchangeId.BITGET, ExchangeId.BITMART],
        reasons=reasons,
    )
