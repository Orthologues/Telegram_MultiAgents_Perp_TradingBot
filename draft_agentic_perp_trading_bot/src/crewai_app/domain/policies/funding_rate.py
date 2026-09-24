"""Deterministic funding-rate filter for new trading-cycle initiation."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from crewai_app.domain.contracts import (
    ExchangeId,
    ExchangeNetwork,
    FundingRateCycleFilterDecision,
    IntentType,
)


DEFAULT_BASELINE_BINANCE_VALUE = Decimal("0.125")
# TODO: Use backtesting to compare the average ROI produced by different
# `DEFAULT_MAXIMUM_BASELINE_MULTIPLIER` values and select the best-performing default.
DEFAULT_MAXIMUM_BASELINE_MULTIPLIER = Decimal("10")
FUNDING_RATE_FILTER_POLICY_VERSION = "funding-rate-cycle-initiation-v1"


def evaluate_funding_rate_cycle_filter(
    *,
    exchange_id: ExchangeId,
    network: ExchangeNetwork,
    symbol: str,
    intent_type: IntentType,
    observed_at: datetime,
    annualized_funding_rate_fraction: Decimal,
    baseline_binance_value: Decimal = DEFAULT_BASELINE_BINANCE_VALUE,
    maximum_baseline_multiplier: Decimal = DEFAULT_MAXIMUM_BASELINE_MULTIPLIER,
) -> FundingRateCycleFilterDecision:
    """Reject new cycles above the strict absolute annualized funding limit."""
    if not annualized_funding_rate_fraction.is_finite():
        raise ValueError("annualized_funding_rate_fraction must be finite")
    if not baseline_binance_value.is_finite() or baseline_binance_value <= 0:
        raise ValueError("baseline_binance_value must be finite and positive")
    if (
        not maximum_baseline_multiplier.is_finite()
        or maximum_baseline_multiplier <= 0
    ):
        raise ValueError("maximum_baseline_multiplier must be finite and positive")

    maximum_absolute_rate = baseline_binance_value * maximum_baseline_multiplier
    applies = intent_type == IntentType.NEW_ORDER
    exceeds_threshold = (
        applies
        and abs(annualized_funding_rate_fraction) > maximum_absolute_rate
    )
    reasons = (
        ["annualized_funding_rate_exceeds_cycle_initiation_threshold"]
        if exceeds_threshold
        else []
    )
    return FundingRateCycleFilterDecision(
        exchange_id=exchange_id,
        network=network,
        symbol=symbol.upper(),
        intent_type=intent_type,
        observed_at=observed_at,
        applied=applies,
        allowed=not exceeds_threshold,
        annualized_funding_rate_fraction=annualized_funding_rate_fraction,
        baseline_binance_value=baseline_binance_value,
        maximum_baseline_multiplier=maximum_baseline_multiplier,
        maximum_absolute_annualized_funding_rate_fraction=maximum_absolute_rate,
        reasons=reasons,
        policy_version=FUNDING_RATE_FILTER_POLICY_VERSION,
    )


__all__ = [
    "DEFAULT_BASELINE_BINANCE_VALUE",
    "DEFAULT_MAXIMUM_BASELINE_MULTIPLIER",
    "FUNDING_RATE_FILTER_POLICY_VERSION",
    "evaluate_funding_rate_cycle_filter",
]
