import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from frameworkless_app.ministral_filter.filter_agent import (
    MinistralFilterAgent,
)
from frameworkless_app.performance_engine.history import (
    InMemoryExecutionHistoryRepository,
)
from frameworkless_app.risk_engine.policy import PairBlacklistPolicy
from frameworkless_app.schemas import (
    ClosedTradeOutcome,
    ExchangeId,
    OwnerId,
    PositionLifecycleEvent,
    SettlementAsset,
    StrategyTier,
)

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def test_ministral_execution_history_is_append_only_and_idempotent() -> None:
    async def scenario() -> None:
        repository = InMemoryExecutionHistoryRepository()
        agent = MinistralFilterAgent(
            "ministral-3-8b",
            execution_history_repository=repository,
        )
        event = PositionLifecycleEvent(
            event_id="fill-1",
            owner_id=OwnerId.OWNER_A_SHU_QIN,
            channel_id="owner_a_channel_a",
            strategy_tier=StrategyTier.INTERMEDIATE,
            exchange_id=ExchangeId.HYPERLIQUID,
            settlement_asset=SettlementAsset.USDC,
            symbol="BTCUSDT",
            position_id="position-1",
            event_type="take_profit_filled",
            realized_pnl_quote=Decimal("5"),
            occurred_at=NOW,
            source_telegram_message_ids=["100"],
        )

        await agent.record_execution_event(event)
        await agent.record_execution_event(event)

        assert repository.events == [event]

    asyncio.run(scenario())


def test_pair_blacklist_uses_recent_net_results_and_stop_reversals() -> None:
    outcomes = [
        ClosedTradeOutcome(
            exchange_id=ExchangeId.HYPERLIQUID,
            settlement_asset=SettlementAsset.USDC,
            symbol="ALTUSDT",
            entry_notional_quote=Decimal("100"),
            closed_at=NOW - timedelta(days=index),
            realized_pnl_quote=Decimal("-1"),
            stopped_out=True,
            reversed_after_stop=index < 7,
        )
        for index in range(7)
    ]
    outcomes.extend(
        ClosedTradeOutcome(
            exchange_id=ExchangeId.HYPERLIQUID,
            settlement_asset=SettlementAsset.USDC,
            symbol="ALTUSDT",
            entry_notional_quote=Decimal("100"),
            closed_at=NOW - timedelta(days=10 + index),
            realized_pnl_quote=Decimal("1"),
        )
        for index in range(3)
    )

    decision = PairBlacklistPolicy().evaluate(
        exchange_id=ExchangeId.HYPERLIQUID,
        symbol="ALTUSDT",
        outcomes=outcomes,
        computed_at=NOW,
    )

    assert decision.blacklisted is True
    assert decision.wins == 3
    assert decision.losses == 7
    assert decision.reasons == [
        "win_loss_ratio_below_threshold",
        "stop_reversal_rate_above_threshold",
    ]
