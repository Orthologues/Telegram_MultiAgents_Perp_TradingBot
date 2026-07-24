import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from agentic_perp_trading_bot.orchestrator import process_message
from agentic_perp_trading_bot.schemas import (
    AssetGroup,
    CanonicalTradeIntent,
    ExchangeId,
    ExchangeTradeState,
    FilterDecision,
    IntentType,
    OwnerId,
    PositionDirection,
    QwenSignalHypothesis,
    StrategyTier,
    TelegramMessageEnvelope,
    TradeAction,
    TradeCursorStatus,
)
from agentic_perp_trading_bot.trade_cursor import (
    ConcurrentTradeCursorManager,
    InMemoryTradeCursorRepository,
    TradeCursorConflictError,
)


NOW = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)


def _message(
    message_id: str,
    *,
    parent_messages: list[str] | None = None,
) -> TelegramMessageEnvelope:
    return TelegramMessageEnvelope(
        owner_id=OwnerId.OWNER_A_SHU_QIN,
        channel_id="owner_a_channel_a",
        asset_group=AssetGroup.MIXED,
        telegram_message_id=message_id,
        received_at=NOW + timedelta(seconds=int(message_id)),
        parent_messages=parent_messages or [],
        dedup_key=f"message-{message_id}",
    )


def _state(
    *,
    exchange_id: ExchangeId,
    symbol: str,
    direction: PositionDirection,
    active_order_ids: set[str],
    open_position_ids: set[str],
    seconds: int = 0,
) -> ExchangeTradeState:
    return ExchangeTradeState(
        exchange_id=exchange_id,
        symbol=symbol,
        direction=direction,
        active_order_ids=active_order_ids,
        open_position_ids=open_position_ids,
        observed_at=NOW + timedelta(seconds=seconds),
    )


def test_parent_chain_resolves_concurrent_pair_cursors_independently() -> None:
    async def scenario() -> None:
        repository = InMemoryTradeCursorRepository()
        manager = ConcurrentTradeCursorManager(repository)
        btc_cursor = await manager.register_exchange_state(
            _message("100"),
            _state(
                exchange_id=ExchangeId.BITMART,
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                active_order_ids={"btc-tp1"},
                open_position_ids={"btc-position"},
            ),
            force_new_cursor=True,
        )
        eth_cursor = await manager.register_exchange_state(
            _message("101", parent_messages=["100"]),
            _state(
                exchange_id=ExchangeId.BITGET,
                symbol="ETHUSDT",
                direction=PositionDirection.SHORT,
                active_order_ids={"eth-tp1"},
                open_position_ids={"eth-position"},
            ),
            force_new_cursor=True,
        )

        incoming = _message("102", parent_messages=["100", "101"])
        candidates = await manager.resolve_for_message(incoming)

        assert {cursor.cursor_id for cursor in candidates} == {
            btc_cursor.cursor_id,
            eth_cursor.cursor_id,
        }

        attached = await manager.attach_message_for_intent(
            incoming,
            CanonicalTradeIntent(
                owner_id=OwnerId.OWNER_A_SHU_QIN,
                channel_id="owner_a_channel_a",
                asset_group=AssetGroup.MIXED,
                strategy_tier=StrategyTier.INTERMEDIATE,
                symbol="BTCUSDT",
                action=TradeAction.REDUCE_LONG,
                order_type="market",
                entries=[Decimal("100000")],
                target_exchanges=[ExchangeId.BITMART],
            ),
            IntentType.CLOSE_POSITION,
        )

        assert [cursor.cursor_id for cursor in attached] == [btc_cursor.cursor_id]
        updated_btc = await repository.get(btc_cursor.cursor_id)
        unchanged_eth = await repository.get(eth_cursor.cursor_id)
        assert updated_btc is not None
        assert updated_btc.message_ids == ["100", "102"]
        assert unchanged_eth is not None
        assert unchanged_eth.message_ids == ["101"]

    asyncio.run(scenario())


def test_cursor_closes_only_after_open_position_and_active_orders_are_gone() -> None:
    async def scenario() -> None:
        repository = InMemoryTradeCursorRepository()
        manager = ConcurrentTradeCursorManager(repository)
        cursor = await manager.register_exchange_state(
            _message("100"),
            _state(
                exchange_id=ExchangeId.BITMART,
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                active_order_ids={"tp1"},
                open_position_ids={"position-1"},
            ),
            force_new_cursor=True,
        )

        position_flat_with_order = await manager.refresh_exchange_state(
            cursor.cursor_id,
            _state(
                exchange_id=ExchangeId.BITMART,
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                active_order_ids={"tp1"},
                open_position_ids=set(),
                seconds=1,
            ),
        )
        assert position_flat_with_order.status == TradeCursorStatus.ACTIVE

        closed = await manager.refresh_exchange_state(
            cursor.cursor_id,
            _state(
                exchange_id=ExchangeId.BITMART,
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                active_order_ids=set(),
                open_position_ids=set(),
                seconds=2,
            ),
        )
        assert closed.status == TradeCursorStatus.CLOSED
        assert closed.closed_at == NOW + timedelta(seconds=2)
        assert await manager.resolve_for_message(
            _message("101", parent_messages=["100"])
        ) == []

    asyncio.run(scenario())


def test_unfilled_order_cursor_does_not_close_as_a_position() -> None:
    async def scenario() -> None:
        repository = InMemoryTradeCursorRepository()
        manager = ConcurrentTradeCursorManager(repository)
        cursor = await manager.register_exchange_state(
            _message("100"),
            _state(
                exchange_id=ExchangeId.BITGET,
                symbol="SOLUSDT",
                direction=PositionDirection.LONG,
                active_order_ids={"entry-order"},
                open_position_ids=set(),
            ),
            force_new_cursor=True,
        )
        refreshed = await manager.refresh_exchange_state(
            cursor.cursor_id,
            _state(
                exchange_id=ExchangeId.BITGET,
                symbol="SOLUSDT",
                direction=PositionDirection.LONG,
                active_order_ids=set(),
                open_position_ids=set(),
                seconds=1,
            ),
        )

        assert refreshed.position_was_opened is False
        assert refreshed.status == TradeCursorStatus.ACTIVE

    asyncio.run(scenario())


def test_cursor_versions_reject_stale_concurrent_writes() -> None:
    async def scenario() -> None:
        repository = InMemoryTradeCursorRepository()
        manager = ConcurrentTradeCursorManager(repository)
        cursor = await manager.register_exchange_state(
            _message("100"),
            _state(
                exchange_id=ExchangeId.BITGET,
                symbol="ETHUSDT",
                direction=PositionDirection.SHORT,
                active_order_ids={"entry-order"},
                open_position_ids=set(),
            ),
            force_new_cursor=True,
        )
        first_update = cursor.model_copy(update={"version": 1})
        stale_update = cursor.model_copy(update={"version": 1})

        await repository.replace(first_update, expected_version=0)
        with pytest.raises(TradeCursorConflictError, match="stale trade cursor"):
            await repository.replace(stale_update, expected_version=0)

    asyncio.run(scenario())


def test_orchestrator_passes_parent_cursor_state_to_agents_and_execution() -> None:
    async def scenario() -> None:
        repository = InMemoryTradeCursorRepository()
        manager = ConcurrentTradeCursorManager(repository)
        cursor = await manager.register_exchange_state(
            _message("100"),
            _state(
                exchange_id=ExchangeId.BITMART,
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                active_order_ids={"tp1"},
                open_position_ids={"position-1"},
            ),
            force_new_cursor=True,
        )
        incoming = _message("101", parent_messages=["100"])
        observed_cursor_ids: list[str] = []

        class QwenStub:
            async def infer_signal(self, message, prompt_context=None):
                observed_cursor_ids.extend(
                    item.cursor_id for item in prompt_context.active_trade_cursors
                )
                prompt_cursor = prompt_context.to_prompt_messages()[-1][
                    "active_trade_cursors"
                ][0]
                assert prompt_cursor["active_order_ids"] == ["tp1"]
                assert prompt_cursor["open_position_ids"] == ["position-1"]
                return QwenSignalHypothesis(
                    owner_id=OwnerId.OWNER_A_SHU_QIN,
                    channel_id="owner_a_channel_a",
                    asset_group=AssetGroup.MIXED,
                    strategy_tier=StrategyTier.INTERMEDIATE,
                    intent_type=IntentType.ADD_POSITION,
                    symbol="BTCUSDT",
                    direction="long",
                    confidence=0.9,
                )

        class MinistralStub:
            async def review(self, hypothesis, prompt_context, market_snapshot=None):
                assert [
                    item.cursor_id for item in prompt_context.active_trade_cursors
                ] == [cursor.cursor_id]
                return FilterDecision(
                    status="approved",
                    quality_score=0.9,
                    canonical_intent=CanonicalTradeIntent(
                        owner_id=OwnerId.OWNER_A_SHU_QIN,
                        channel_id="owner_a_channel_a",
                        asset_group=AssetGroup.MIXED,
                        strategy_tier=StrategyTier.INTERMEDIATE,
                        symbol="BTCUSDT",
                        action=TradeAction.OPEN_LONG,
                        order_type="limit",
                        entries=[Decimal("100000")],
                        stop_loss=Decimal("95000"),
                        target_exchanges=[ExchangeId.BITMART],
                    ),
                    reviewer_model="ministral-test",
                )

        request = await process_message(
            incoming,
            QwenStub(),
            MinistralStub(),
            trade_cursor_manager=manager,
        )

        assert request is not None
        assert observed_cursor_ids == [cursor.cursor_id]
        assert request.trade_cursor_ids == [cursor.cursor_id]
        assert request.parent_message_ids == ["100"]
        updated = await repository.get(cursor.cursor_id)
        assert updated is not None
        assert updated.message_ids == ["100", "101"]

    asyncio.run(scenario())
