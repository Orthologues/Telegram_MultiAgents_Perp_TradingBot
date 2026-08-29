"""Paired Aster and Hyperliquid testnet P/L comparison."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from agentic_perp_trading_bot.schemas import (
    ClosedTradeOutcome,
    ExchangeId,
    ExchangeNetwork,
    SettlementAsset,
    TestnetVenuePerformanceComparison,
    VenuePerformanceSummary,
)


def compare_testnet_venue_performance(
    outcomes: list[ClosedTradeOutcome],
    *,
    computed_at: datetime | None = None,
) -> TestnetVenuePerformanceComparison:
    """Compare only closed positions produced by signals executed on both testnets."""
    totals: dict[tuple[str, ExchangeId], tuple[Decimal, Decimal]] = defaultdict(
        lambda: (Decimal("0"), Decimal("0"))
    )
    for outcome in outcomes:
        if outcome.network != ExchangeNetwork.TESTNET or not outcome.signal_dedup_key:
            continue
        key = (outcome.signal_dedup_key, outcome.exchange_id)
        net_pnl, entry_notional = totals[key]
        totals[key] = (
            net_pnl + outcome.net_pnl_quote,
            entry_notional + outcome.entry_notional_quote,
        )

    aster_keys = {
        signal_key for signal_key, exchange_id in totals if exchange_id == ExchangeId.ASTER
    }
    hyperliquid_keys = {
        signal_key for signal_key, exchange_id in totals if exchange_id == ExchangeId.HYPERLIQUID
    }
    matched_signal_keys = sorted(aster_keys.intersection(hyperliquid_keys))

    aster = _summarize(
        ExchangeId.ASTER,
        SettlementAsset.USDT,
        matched_signal_keys,
        totals,
    )
    hyperliquid = _summarize(
        ExchangeId.HYPERLIQUID,
        SettlementAsset.USDC,
        matched_signal_keys,
        totals,
    )
    higher_net_pnl_exchange: ExchangeId | None = None
    if aster.net_pnl_percentage > hyperliquid.net_pnl_percentage:
        higher_net_pnl_exchange = ExchangeId.ASTER
    elif hyperliquid.net_pnl_percentage > aster.net_pnl_percentage:
        higher_net_pnl_exchange = ExchangeId.HYPERLIQUID

    return TestnetVenuePerformanceComparison(
        matched_signal_keys=matched_signal_keys,
        aster=aster,
        hyperliquid=hyperliquid,
        higher_net_pnl_exchange=higher_net_pnl_exchange,
        computed_at=computed_at or datetime.now(timezone.utc),
    )


def _summarize(
    exchange_id: ExchangeId,
    settlement_asset: SettlementAsset,
    matched_signal_keys: list[str],
    totals: dict[tuple[str, ExchangeId], tuple[Decimal, Decimal]],
) -> VenuePerformanceSummary:
    percentages = [
        net_pnl / entry_notional * Decimal("100")
        for signal_key in matched_signal_keys
        for net_pnl, entry_notional in [totals[(signal_key, exchange_id)]]
    ]
    profits = [value for value in percentages if value > 0]
    losses = [value for value in percentages if value < 0]
    net_pnl = sum(percentages, start=Decimal("0"))
    gross_profit = sum(profits, start=Decimal("0"))
    gross_loss = -sum(losses, start=Decimal("0"))
    count = len(percentages)

    return VenuePerformanceSummary(
        exchange_id=exchange_id,
        settlement_asset=settlement_asset,
        matched_signals=count,
        profitable_signals=len(profits),
        losing_signals=len(losses),
        breakeven_signals=count - len(profits) - len(losses),
        gross_profit_percentage=gross_profit,
        gross_loss_percentage=gross_loss,
        net_pnl_percentage=net_pnl,
        mean_pnl_percentage=net_pnl / count if count else Decimal("0"),
        profit_loss_ratio=(gross_profit / gross_loss if gross_loss > 0 else None),
    )
