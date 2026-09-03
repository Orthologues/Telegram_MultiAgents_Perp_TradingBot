from datetime import datetime, timezone
from decimal import Decimal

from frameworkless_app.performance_engine import (
    compare_testnet_venue_performance,
)
from frameworkless_app.schemas import (
    ClosedTradeOutcome,
    ExchangeId,
    ExchangeNetwork,
    SettlementAsset,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


def _outcome(
    *,
    signal: str,
    exchange_id: ExchangeId,
    pnl: str,
    network: ExchangeNetwork = ExchangeNetwork.TESTNET,
) -> ClosedTradeOutcome:
    return ClosedTradeOutcome(
        exchange_id=exchange_id,
        network=network,
        settlement_asset=(
            SettlementAsset.USDT if exchange_id == ExchangeId.ASTER else SettlementAsset.USDC
        ),
        symbol="BTC",
        signal_dedup_key=signal,
        entry_notional_quote=Decimal("100"),
        closed_at=NOW,
        realized_pnl_quote=Decimal(pnl),
    )


def test_comparison_uses_only_identical_signals_executed_on_both_testnets() -> None:
    comparison = compare_testnet_venue_performance(
        [
            _outcome(signal="shared-win", exchange_id=ExchangeId.ASTER, pnl="10"),
            _outcome(
                signal="shared-win",
                exchange_id=ExchangeId.HYPERLIQUID,
                pnl="5",
            ),
            _outcome(signal="shared-loss", exchange_id=ExchangeId.ASTER, pnl="-5"),
            _outcome(
                signal="shared-loss",
                exchange_id=ExchangeId.HYPERLIQUID,
                pnl="-10",
            ),
            _outcome(signal="aster-only", exchange_id=ExchangeId.ASTER, pnl="50"),
            _outcome(
                signal="mainnet-pair",
                exchange_id=ExchangeId.ASTER,
                pnl="50",
                network=ExchangeNetwork.MAINNET,
            ),
            _outcome(
                signal="mainnet-pair",
                exchange_id=ExchangeId.HYPERLIQUID,
                pnl="50",
                network=ExchangeNetwork.MAINNET,
            ),
        ],
        computed_at=NOW,
    )

    assert comparison.matched_signal_keys == ["shared-loss", "shared-win"]
    assert comparison.aster.matched_signals == 2
    assert comparison.aster.net_pnl_percentage == Decimal("5")
    assert comparison.aster.profit_loss_ratio == Decimal("2")
    assert comparison.hyperliquid.net_pnl_percentage == Decimal("-5")
    assert comparison.hyperliquid.profit_loss_ratio == Decimal("0.5")
    assert comparison.higher_net_pnl_exchange == ExchangeId.ASTER


def test_empty_intersection_returns_a_neutral_comparison() -> None:
    comparison = compare_testnet_venue_performance(
        [_outcome(signal="aster-only", exchange_id=ExchangeId.ASTER, pnl="10")],
        computed_at=NOW,
    )

    assert comparison.matched_signal_keys == []
    assert comparison.aster.net_pnl_percentage == Decimal("0")
    assert comparison.hyperliquid.net_pnl_percentage == Decimal("0")
    assert comparison.higher_net_pnl_exchange is None
