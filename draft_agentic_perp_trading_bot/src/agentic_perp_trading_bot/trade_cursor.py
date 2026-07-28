"""Concurrent parent-message trade cursors and DynamoDB repository boundary."""

from __future__ import annotations

import hashlib
from asyncio import Lock
from typing import Protocol

from agentic_perp_trading_bot.schemas import (
    CanonicalTradeIntent,
    ExchangeTradeState,
    IntentType,
    LifecycleStrategySource,
    OwnerId,
    PositionLifecycleStrategy,
    PositionDirection,
    TelegramMessageEnvelope,
    TradeAction,
    TradeCursorStatus,
    TradeThreadCursor,
)


class TradeCursorConflictError(RuntimeError):
    """Raised when a conditional cursor write observes a stale version."""


class AmbiguousTradeCursorError(RuntimeError):
    """Raised when one parent chain matches multiple cursors for one trade identity."""


class DynamoDBTradeCursorRepository(Protocol):
    """Production repository contract for DynamoDB-backed live cursor metadata."""

    async def list_active_by_parent_messages(
        self,
        *,
        owner_id: OwnerId,
        channel_id: str,
        parent_message_ids: list[str],
    ) -> list[TradeThreadCursor]: ...

    async def get(self, cursor_id: str) -> TradeThreadCursor | None: ...

    async def create(self, cursor: TradeThreadCursor) -> None: ...

    async def replace(
        self,
        cursor: TradeThreadCursor,
        *,
        expected_version: int,
    ) -> None: ...


class InMemoryTradeCursorRepository:
    """Concurrent test adapter matching the DynamoDB conditional-write contract."""

    def __init__(self, cursors: list[TradeThreadCursor] | None = None) -> None:
        self._cursors = {
            cursor.cursor_id: cursor.model_copy(deep=True)
            for cursor in (cursors or [])
        }
        self._lock = Lock()

    async def list_active_by_parent_messages(
        self,
        *,
        owner_id: OwnerId,
        channel_id: str,
        parent_message_ids: list[str],
    ) -> list[TradeThreadCursor]:
        parent_ids = set(parent_message_ids)
        if not parent_ids:
            return []
        async with self._lock:
            matches = [
                cursor.model_copy(deep=True)
                for cursor in self._cursors.values()
                if cursor.status == TradeCursorStatus.ACTIVE
                and cursor.owner_id == owner_id
                and cursor.channel_id == channel_id
                and parent_ids.intersection(cursor.message_ids)
            ]
        return sorted(matches, key=lambda cursor: cursor.cursor_id)

    async def get(self, cursor_id: str) -> TradeThreadCursor | None:
        async with self._lock:
            cursor = self._cursors.get(cursor_id)
            return cursor.model_copy(deep=True) if cursor is not None else None

    async def create(self, cursor: TradeThreadCursor) -> None:
        async with self._lock:
            if cursor.cursor_id in self._cursors:
                raise TradeCursorConflictError(
                    f"trade cursor already exists: {cursor.cursor_id}"
                )
            self._cursors[cursor.cursor_id] = cursor.model_copy(deep=True)

    async def replace(
        self,
        cursor: TradeThreadCursor,
        *,
        expected_version: int,
    ) -> None:
        async with self._lock:
            current = self._cursors.get(cursor.cursor_id)
            if current is None:
                raise TradeCursorConflictError(
                    f"trade cursor does not exist: {cursor.cursor_id}"
                )
            if current.version != expected_version:
                raise TradeCursorConflictError(
                    f"stale trade cursor {cursor.cursor_id}: "
                    f"expected version {expected_version}, got {current.version}"
                )
            if cursor.version != expected_version + 1:
                raise ValueError("replacement cursor version must increment by one")
            self._cursors[cursor.cursor_id] = cursor.model_copy(deep=True)


class ConcurrentTradeCursorManager:
    """Resolve and maintain independent live cursors from Telegram parent chains."""

    def __init__(self, repository: DynamoDBTradeCursorRepository) -> None:
        self._repository = repository

    async def resolve_for_message(
        self,
        message: TelegramMessageEnvelope,
    ) -> list[TradeThreadCursor]:
        return await self._repository.list_active_by_parent_messages(
            owner_id=message.owner_id,
            channel_id=message.channel_id,
            parent_message_ids=message.parent_messages,
        )

    async def attach_message_for_intent(
        self,
        message: TelegramMessageEnvelope,
        intent: CanonicalTradeIntent,
        intent_type: IntentType,
        candidates: list[TradeThreadCursor] | None = None,
        lifecycle_strategy: PositionLifecycleStrategy | None = None,
    ) -> list[TradeThreadCursor]:
        """Attach a continuation to matching active pair/exchange cursors."""
        if intent_type == IntentType.NEW_ORDER:
            return []

        if candidates is None:
            candidates = await self.resolve_for_message(message)
        direction = _direction_for_action(intent.action)
        attached: list[TradeThreadCursor] = []
        for exchange_id in dict.fromkeys(intent.target_exchanges):
            matches = [
                cursor
                for cursor in candidates
                if cursor.exchange_id == exchange_id
                and cursor.symbol.upper() == intent.symbol.upper()
                and cursor.direction == direction
            ]
            if len(matches) > 1:
                raise AmbiguousTradeCursorError(
                    f"multiple active cursors match {exchange_id}:{intent.symbol}:{direction}"
                )
            if matches:
                attached.append(
                    await self._append_message(
                        matches[0],
                        message,
                        lifecycle_strategy=lifecycle_strategy,
                    )
                )
        return attached

    async def register_exchange_state(
        self,
        message: TelegramMessageEnvelope,
        state: ExchangeTradeState,
        *,
        lifecycle_strategy: PositionLifecycleStrategy,
        force_new_cursor: bool = False,
    ) -> TradeThreadCursor:
        """Create or update a cursor after MCP returns live exchange state."""
        candidates = [] if force_new_cursor else await self.resolve_for_message(message)
        matches = [
            cursor
            for cursor in candidates
            if cursor.exchange_id == state.exchange_id
            and cursor.symbol.upper() == state.symbol.upper()
            and cursor.direction == state.direction
        ]
        if len(matches) > 1:
            raise AmbiguousTradeCursorError(
                f"multiple active cursors match "
                f"{state.exchange_id}:{state.symbol}:{state.direction}"
            )
        if matches:
            return await self._replace_from_state(
                matches[0],
                message,
                state,
                lifecycle_strategy=lifecycle_strategy,
            )
        if not state.active_order_ids and not state.open_position_ids:
            raise ValueError(
                "a new trade cursor requires an active order or open position"
            )

        cursor = TradeThreadCursor(
            cursor_id=_cursor_id(message, state),
            owner_id=message.owner_id,
            channel_id=message.channel_id,
            origin_message_id=message.telegram_message_id,
            message_ids=[message.telegram_message_id],
            exchange_id=state.exchange_id,
            symbol=state.symbol.upper(),
            direction=state.direction,
            active_order_ids=set(state.active_order_ids),
            open_position_ids=set(state.open_position_ids),
            lifecycle_strategy=lifecycle_strategy,
            position_was_opened=bool(state.open_position_ids),
            opened_at=state.observed_at,
            updated_at=state.observed_at,
        )
        await self._repository.create(cursor)
        return cursor

    async def refresh_exchange_state(
        self,
        cursor_id: str,
        state: ExchangeTradeState,
    ) -> TradeThreadCursor:
        """Refresh live IDs and close only after the position is fully flat."""
        cursor = await self._repository.get(cursor_id)
        if cursor is None:
            raise KeyError(f"unknown trade cursor: {cursor_id}")
        _validate_state_identity(cursor, state)
        if cursor.status == TradeCursorStatus.CLOSED:
            if state.active_order_ids or state.open_position_ids:
                raise ValueError("a closed trade cursor cannot be reactivated")
            return cursor
        return await self._replace_from_state(cursor, None, state)

    async def _append_message(
        self,
        cursor: TradeThreadCursor,
        message: TelegramMessageEnvelope,
        *,
        lifecycle_strategy: PositionLifecycleStrategy | None = None,
    ) -> TradeThreadCursor:
        next_strategy = _resolve_lifecycle_strategy(
            cursor,
            message,
            lifecycle_strategy,
        )
        if (
            message.telegram_message_id in cursor.message_ids
            and next_strategy == cursor.lifecycle_strategy
        ):
            return cursor
        message_ids = sorted(
            [*cursor.message_ids, message.telegram_message_id],
            key=int,
        )
        updated = TradeThreadCursor.model_validate(
            {
                **cursor.model_dump(),
                "message_ids": message_ids,
                "lifecycle_strategy": next_strategy,
                "updated_at": max(cursor.updated_at, message.received_at),
                "version": cursor.version + 1,
            }
        )
        await self._repository.replace(updated, expected_version=cursor.version)
        return updated

    async def _replace_from_state(
        self,
        cursor: TradeThreadCursor,
        message: TelegramMessageEnvelope | None,
        state: ExchangeTradeState,
        *,
        lifecycle_strategy: PositionLifecycleStrategy | None = None,
    ) -> TradeThreadCursor:
        _validate_state_identity(cursor, state)
        message_ids = list(cursor.message_ids)
        if message is not None and message.telegram_message_id not in message_ids:
            message_ids.append(message.telegram_message_id)
            message_ids.sort(key=int)
        next_strategy = (
            _resolve_lifecycle_strategy(cursor, message, lifecycle_strategy)
            if message is not None
            else cursor.lifecycle_strategy
        )

        position_was_opened = cursor.position_was_opened or bool(
            state.open_position_ids
        )
        fully_closed = (
            position_was_opened
            and not state.open_position_ids
            and not state.active_order_ids
        )
        updated = TradeThreadCursor.model_validate(
            {
                **cursor.model_dump(),
                "message_ids": message_ids,
                "active_order_ids": set(state.active_order_ids),
                "open_position_ids": set(state.open_position_ids),
                "lifecycle_strategy": next_strategy,
                "position_was_opened": position_was_opened,
                "status": (
                    TradeCursorStatus.CLOSED
                    if fully_closed
                    else TradeCursorStatus.ACTIVE
                ),
                "closed_at": state.observed_at if fully_closed else None,
                "updated_at": state.observed_at,
                "version": cursor.version + 1,
            }
        )
        await self._repository.replace(updated, expected_version=cursor.version)
        return updated


def _cursor_id(
    message: TelegramMessageEnvelope,
    state: ExchangeTradeState,
) -> str:
    identity = ":".join(
        (
            message.owner_id,
            message.channel_id,
            message.telegram_message_id,
            state.exchange_id,
            state.symbol.upper(),
            state.direction,
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]


def _direction_for_action(action: TradeAction) -> PositionDirection:
    if action in (
        TradeAction.OPEN_LONG,
        TradeAction.CLOSE_LONG,
        TradeAction.REDUCE_LONG,
    ):
        return PositionDirection.LONG
    return PositionDirection.SHORT


def _validate_state_identity(
    cursor: TradeThreadCursor,
    state: ExchangeTradeState,
) -> None:
    identity = (cursor.exchange_id, cursor.symbol.upper(), cursor.direction)
    state_identity = (state.exchange_id, state.symbol.upper(), state.direction)
    if identity != state_identity:
        raise ValueError(
            f"exchange state {state_identity} does not match cursor {identity}"
        )


def _resolve_lifecycle_strategy(
    cursor: TradeThreadCursor,
    message: TelegramMessageEnvelope,
    proposed: PositionLifecycleStrategy | None,
) -> PositionLifecycleStrategy:
    current = cursor.lifecycle_strategy
    if proposed is None or proposed == current:
        return current
    if proposed.source != LifecycleStrategySource.TELEGRAM_TRANSITION:
        raise ValueError("only a Telegram transition may replace a lifecycle strategy")
    if proposed.revision != current.revision + 1:
        raise ValueError("a lifecycle strategy transition must increment revision by one")
    if proposed.source_telegram_message_id != message.telegram_message_id:
        raise ValueError("a lifecycle strategy transition must cite the current message")
    if not set(message.parent_messages).intersection(cursor.message_ids):
        raise ValueError("a lifecycle strategy transition must be parent-linked")
    return proposed
