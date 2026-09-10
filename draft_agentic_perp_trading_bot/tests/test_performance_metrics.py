from datetime import datetime, timezone
from decimal import Decimal

from crewai_app.domain.contracts.schemas import (
    AssetGroup,
    ClosedTradeOutcome,
    ExchangeId,
    OwnerId,
    SettlementAsset,
    StrategyOutcome,
    StrategyTier,
)
from crewai_app.domain.performance.metrics import summarize_strategy_dimensions


NOW = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)


def _outcome(
    *,
    outcome_id: str,
    tier: StrategyTier,
    pnl: str,
    fully_closed: bool = True,
) -> StrategyOutcome:
    return StrategyOutcome(
        strategy_tier=tier,
        outcome=ClosedTradeOutcome(
            exchange_id=ExchangeId.ASTER,
            settlement_asset=SettlementAsset.USDT,
            symbol="BTCUSDT",
            signal_dedup_key="signal-1",
            strategy_tier=tier,
            outcome_id=outcome_id,
            fully_closed=fully_closed,
            owner_id=OwnerId.OWNER_A_SHU_QIN,
            channel_id="owner-a-btc",
            asset_group=AssetGroup.BTC_ETH,
            lifecycle_stage="continuation",
            entry_notional_quote=Decimal("100"),
            closed_at=NOW,
            realized_pnl_quote=Decimal(pnl),
        ),
    )


def test_strategy_performance_preserves_dimensions_and_deduplicates_outcomes() -> None:
    summaries = summarize_strategy_dimensions(
        [
            _outcome(
                outcome_id="outcome-1",
                tier=StrategyTier.INTERMEDIATE,
                pnl="5",
            ),
            _outcome(
                outcome_id="outcome-1",
                tier=StrategyTier.INTERMEDIATE,
                pnl="500",
            ),
            _outcome(
                outcome_id="open-1",
                tier=StrategyTier.RADICAL,
                pnl="20",
                fully_closed=False,
            ),
        ]
    )

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.strategy_tier == StrategyTier.INTERMEDIATE
    assert summary.owner_id == OwnerId.OWNER_A_SHU_QIN
    assert summary.channel_id == "owner-a-btc"
    assert summary.asset_group == AssetGroup.BTC_ETH
    assert summary.lifecycle_stage == "continuation"
    assert summary.sample_count == 1
    assert summary.executed_net_pnl_percentage == Decimal("5")
