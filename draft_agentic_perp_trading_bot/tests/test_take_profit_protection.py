import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from agentic_perp_trading_bot.ministral_filter.filter_agent import (
    MinistralFilterAgent,
)
from agentic_perp_trading_bot.ministral_filter.take_profit_protection import (
    TakeProfitProtectionPolicy,
)
from agentic_perp_trading_bot.schemas import (
    ExchangeId,
    PositionDirection,
    TakeProfitFillEvent,
    TakeProfitLevel,
    TakeProfitProtectionAction,
)


def _event(
    *,
    direction: PositionDirection = PositionDirection.LONG,
    triggered_level: TakeProfitLevel = TakeProfitLevel.TP1,
    configured_levels: list[TakeProfitLevel] | None = None,
    filled_levels: list[TakeProfitLevel] | None = None,
    current_stop_loss: Decimal | None = None,
) -> TakeProfitFillEvent:
    if configured_levels is None:
        configured_levels = [
            TakeProfitLevel.TP1,
            TakeProfitLevel.TP2,
            TakeProfitLevel.TP3,
        ]
    if filled_levels is None:
        filled_levels = [TakeProfitLevel.TP1]
    long_position = direction == PositionDirection.LONG
    return TakeProfitFillEvent(
        event_id="fill-123",
        exchange_id=ExchangeId.BITMART,
        symbol="BTCUSDT",
        position_id="position-1",
        direction=direction,
        triggered_level=triggered_level,
        configured_levels=configured_levels,
        filled_levels=filled_levels,
        average_entry_price=Decimal("100"),
        tp1_price=Decimal("110") if long_position else Decimal("90"),
        current_stop_loss=current_stop_loss,
        occurred_at=datetime.now(timezone.utc),
    )


def test_tp1_long_moves_stop_point_one_five_percent_above_entry() -> None:
    decision = TakeProfitProtectionPolicy().evaluate(_event())

    assert decision.action == TakeProfitProtectionAction.MOVE_TO_PROTECTED_ENTRY
    assert decision.requested_stop_loss == Decimal("100.1500")


def test_tp1_short_moves_stop_point_one_five_percent_below_entry() -> None:
    decision = TakeProfitProtectionPolicy().evaluate(
        _event(direction=PositionDirection.SHORT)
    )

    assert decision.action == TakeProfitProtectionAction.MOVE_TO_PROTECTED_ENTRY
    assert decision.requested_stop_loss == Decimal("99.8500")


def test_tp2_moves_stop_to_tp1_while_tp3_is_pending() -> None:
    decision = TakeProfitProtectionPolicy().evaluate(
        _event(
            triggered_level=TakeProfitLevel.TP2,
            filled_levels=[TakeProfitLevel.TP1, TakeProfitLevel.TP2],
        )
    )

    assert decision.action == TakeProfitProtectionAction.MOVE_TO_TP1
    assert decision.requested_stop_loss == Decimal("110")


def test_tp2_does_not_move_stop_when_tp3_is_not_configured() -> None:
    decision = TakeProfitProtectionPolicy().evaluate(
        _event(
            triggered_level=TakeProfitLevel.TP2,
            configured_levels=[TakeProfitLevel.TP1, TakeProfitLevel.TP2],
            filled_levels=[TakeProfitLevel.TP1, TakeProfitLevel.TP2],
        )
    )

    assert decision.action == TakeProfitProtectionAction.NO_CHANGE
    assert decision.requested_stop_loss is None
    assert "tp3_is_not_pending" in decision.reasons


def test_policy_never_loosens_an_existing_stop() -> None:
    decision = TakeProfitProtectionPolicy().evaluate(
        _event(current_stop_loss=Decimal("105"))
    )

    assert decision.action == TakeProfitProtectionAction.NO_CHANGE
    assert decision.requested_stop_loss is None
    assert "existing_stop_is_already_tighter" in decision.reasons


def test_tp2_event_requires_tp1_to_have_filled_first() -> None:
    with pytest.raises(ValidationError, match="TP2 protection requires TP1"):
        _event(
            triggered_level=TakeProfitLevel.TP2,
            configured_levels=[TakeProfitLevel.TP2, TakeProfitLevel.TP3],
            filled_levels=[TakeProfitLevel.TP2],
        )


def test_ministral_api_returns_idempotent_mcp_decision() -> None:
    event = _event()
    decision = asyncio.run(
        MinistralFilterAgent("ministral-3-8b").protect_entry_after_take_profit(event)
    )

    assert decision.event_id == event.event_id
    assert decision.idempotency_key == "take-profit-protection:fill-123"
