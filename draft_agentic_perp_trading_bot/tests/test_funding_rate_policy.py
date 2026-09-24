from datetime import datetime, timezone
from decimal import Decimal

import pytest

from crewai_app.domain.contracts import (
    ExchangeId,
    ExchangeNetwork,
    FundingRateCycleFilterDecision,
    IntentType,
)
from crewai_app.domain.policies.funding_rate import (
    DEFAULT_BASELINE_BINANCE_VALUE,
    DEFAULT_MAXIMUM_BASELINE_MULTIPLIER,
    evaluate_funding_rate_cycle_filter,
)


def _evaluate(
    annualized_rate: str,
    *,
    intent_type: IntentType = IntentType.NEW_ORDER,
) -> FundingRateCycleFilterDecision:
    return evaluate_funding_rate_cycle_filter(
        exchange_id=ExchangeId.ASTER,
        network=ExchangeNetwork.TESTNET,
        symbol="BTCUSDT",
        intent_type=intent_type,
        observed_at=datetime(2026, 9, 24, tzinfo=timezone.utc),
        annualized_funding_rate_fraction=Decimal(annualized_rate),
    )


@pytest.mark.parametrize("annualized_rate", ["1.25", "-1.25"])
def test_cycle_initiation_allows_absolute_rate_at_threshold(
    annualized_rate: str,
) -> None:
    decision = _evaluate(annualized_rate)

    assert DEFAULT_BASELINE_BINANCE_VALUE == Decimal("0.125")
    assert DEFAULT_MAXIMUM_BASELINE_MULTIPLIER == Decimal("10")
    assert decision.maximum_absolute_annualized_funding_rate_fraction == Decimal(
        "1.250"
    )
    assert decision.applied is True
    assert decision.allowed is True
    assert decision.reasons == []


@pytest.mark.parametrize("annualized_rate", ["1.250001", "-1.250001"])
def test_cycle_initiation_rejects_absolute_rate_above_threshold(
    annualized_rate: str,
) -> None:
    decision = _evaluate(annualized_rate)

    assert decision.allowed is False
    assert decision.reasons == [
        "annualized_funding_rate_exceeds_cycle_initiation_threshold"
    ]


def test_existing_cycle_intent_is_not_filtered_by_funding_rate() -> None:
    decision = _evaluate("9.0", intent_type=IntentType.ADD_POSITION)

    assert decision.applied is False
    assert decision.allowed is True
    assert decision.reasons == []


@pytest.mark.parametrize(
    ("baseline", "multiplier", "message"),
    [
        (Decimal("0"), Decimal("10"), "baseline_binance_value"),
        (Decimal("0.125"), Decimal("0"), "maximum_baseline_multiplier"),
    ],
)
def test_funding_rate_filter_rejects_invalid_policy_configuration(
    baseline: Decimal,
    multiplier: Decimal,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        evaluate_funding_rate_cycle_filter(
            exchange_id=ExchangeId.ASTER,
            network=ExchangeNetwork.TESTNET,
            symbol="BTCUSDT",
            intent_type=IntentType.NEW_ORDER,
            observed_at=datetime(2026, 9, 24, tzinfo=timezone.utc),
            annualized_funding_rate_fraction=Decimal("0.1"),
            baseline_binance_value=baseline,
            maximum_baseline_multiplier=multiplier,
        )
