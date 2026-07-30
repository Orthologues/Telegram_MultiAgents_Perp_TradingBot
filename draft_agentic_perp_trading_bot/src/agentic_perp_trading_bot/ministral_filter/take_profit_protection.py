"""Deterministic stop protection after MCP-reported take-profit fills."""

from __future__ import annotations

from decimal import Decimal

from agentic_perp_trading_bot.schemas import (
    PositionDirection,
    TakeProfitFillEvent,
    TakeProfitLevel,
    TakeProfitProtectionAction,
    TakeProfitProtectionDecision,
)

ENTRY_PROFIT_OFFSET = Decimal("0.0015")
POLICY_VERSION = "take-profit-entry-protection-v1"


class TakeProfitProtectionPolicy:
    def evaluate(self, event: TakeProfitFillEvent) -> TakeProfitProtectionDecision:
        action = TakeProfitProtectionAction.NO_CHANGE
        requested_stop: Decimal | None = None
        reasons = [f"{event.triggered_level.value.lower()}_fill"]

        if event.triggered_level == TakeProfitLevel.TP1:
            action = TakeProfitProtectionAction.MOVE_TO_PROTECTED_ENTRY
            if event.direction == PositionDirection.LONG:
                requested_stop = event.average_entry_price * (
                    Decimal("1") + ENTRY_PROFIT_OFFSET
                )
            else:
                requested_stop = event.average_entry_price * (
                    Decimal("1") - ENTRY_PROFIT_OFFSET
                )
        elif (
            event.triggered_level == TakeProfitLevel.TP2
            and TakeProfitLevel.TP3 in event.configured_levels
            and TakeProfitLevel.TP3 not in event.filled_levels
        ):
            action = TakeProfitProtectionAction.MOVE_TO_TP1
            requested_stop = event.tp1_price
        elif event.triggered_level == TakeProfitLevel.TP2:
            reasons.append("tp3_is_not_pending")

        if requested_stop is not None and not self._tightens_stop(event, requested_stop):
            action = TakeProfitProtectionAction.NO_CHANGE
            requested_stop = None
            reasons.append("existing_stop_is_already_tighter")

        return TakeProfitProtectionDecision(
            event_id=event.event_id,
            exchange_id=event.exchange_id,
            network=event.network,
            settlement_asset=event.settlement_asset,
            symbol=event.symbol,
            position_id=event.position_id,
            action=action,
            requested_stop_loss=requested_stop,
            trigger_level=event.triggered_level,
            policy_version=POLICY_VERSION,
            idempotency_key=f"take-profit-protection:{event.event_id}",
            reasons=reasons,
        )

    @staticmethod
    def _tightens_stop(
        event: TakeProfitFillEvent,
        requested_stop: Decimal,
    ) -> bool:
        if event.current_stop_loss is None:
            return True
        if event.direction == PositionDirection.LONG:
            return requested_stop > event.current_stop_loss
        return requested_stop < event.current_stop_loss
