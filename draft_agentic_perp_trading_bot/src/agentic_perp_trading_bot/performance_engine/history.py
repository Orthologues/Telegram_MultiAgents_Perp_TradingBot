"""DynamoDB execution-history boundary for replayable performance features."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from agentic_perp_trading_bot.schemas import ExchangeId, PositionLifecycleEvent


class DynamoDBExecutionHistoryRepository(Protocol):
    async def append(self, event: PositionLifecycleEvent) -> None: ...

    async def list_by_position(
        self,
        *,
        exchange_id: ExchangeId,
        position_id: str,
    ) -> list[PositionLifecycleEvent]: ...


class InMemoryExecutionHistoryRepository:
    """Test adapter preserving the append-only lifecycle contract."""

    def __init__(self, events: Iterable[PositionLifecycleEvent] = ()) -> None:
        self.events = list(events)
        self._event_ids = {event.event_id for event in self.events}

    async def append(self, event: PositionLifecycleEvent) -> None:
        if event.event_id in self._event_ids:
            return
        self._event_ids.add(event.event_id)
        self.events.append(event)

    async def list_by_position(
        self,
        *,
        exchange_id: ExchangeId,
        position_id: str,
    ) -> list[PositionLifecycleEvent]:
        return sorted(
            (
                event
                for event in self.events
                if event.exchange_id == exchange_id
                and event.position_id == position_id
            ),
            key=lambda event: event.occurred_at,
        )
