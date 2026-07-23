"""AG2 TelegramAgent polling and durable-cursor boundaries.

AG2's TelegramAgent retrieval tool is pull-based. This scaffold keeps retrieval
separate from cursor commit so callers can persist media and metadata before the
cursor advances, providing at-least-once delivery.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Protocol, Self

from agentic_perp_trading_bot.schemas import (
    TelegramAgentChannelConfig,
    TelegramAgentPollBatch,
    TelegramAgentRetrievalBatch,
)
from agentic_perp_trading_bot.skills_api import TelegramAgentAPI
from agentic_perp_trading_bot.telegram_ingestion.normalizer import (
    normalize_telegram_agent_message,
)


class TelegramRetrieveCallable(Protocol):
    """Retrieval-only wrapper around one configured AG2 TelegramAgent tool."""

    def __call__(
        self,
        *,
        messages_since: str | None,
        maximum_messages: int | None,
    ) -> Awaitable[dict[str, Any] | str]: ...


class TelegramCursorStore(Protocol):
    async def load(self, channel_id: str) -> str | None: ...

    async def advance(
        self,
        channel_id: str,
        *,
        expected_message_id: str | None,
        new_message_id: str,
    ) -> None: ...


class CursorConflictError(RuntimeError):
    """Raised when another worker has already advanced a channel cursor."""


class CallableTelegramAgentRetriever:
    """Validate the structured output of an AG2 TelegramAgent retrieve call.

    The callable must expose only retrieval. Do not register TelegramSendTool in
    this worker's executor.
    """

    def __init__(
        self,
        *,
        telegram_chat_id: str,
        retrieve: TelegramRetrieveCallable,
    ) -> None:
        self.telegram_chat_id = telegram_chat_id
        self._retrieve = retrieve

    @classmethod
    def from_telegram_agent(
        cls,
        *,
        telegram_chat_id: str,
        telegram_agent: Any,
    ) -> Self:
        """Select the retrieve tool without exposing TelegramSendTool."""
        retrieve_tools = [
            tool for tool in getattr(telegram_agent, "tools", []) if tool.name == "telegram_retrieve"
        ]
        if len(retrieve_tools) != 1:
            raise ValueError("TelegramAgent must expose exactly one telegram_retrieve tool")
        return cls(telegram_chat_id=telegram_chat_id, retrieve=retrieve_tools[0].func)

    async def retrieve_messages(
        self,
        *,
        messages_since: str | None,
        maximum_messages: int | None,
    ) -> TelegramAgentRetrievalBatch:
        payload = await self._retrieve(
            messages_since=messages_since,
            maximum_messages=maximum_messages,
        )
        if not isinstance(payload, dict):
            raise RuntimeError(f"AG2 Telegram retrieval failed: {payload}")

        return TelegramAgentRetrievalBatch.model_validate(
            {**payload, "telegram_chat_id": self.telegram_chat_id}
        )


class InMemoryTelegramCursorStore:
    """Process-local compare-and-set cursor store for tests only."""

    def __init__(self, cursors: Mapping[str, str] | None = None) -> None:
        self._cursors = dict(cursors or {})

    async def load(self, channel_id: str) -> str | None:
        return self._cursors.get(channel_id)

    async def advance(
        self,
        channel_id: str,
        *,
        expected_message_id: str | None,
        new_message_id: str,
    ) -> None:
        current = self._cursors.get(channel_id)
        if current != expected_message_id:
            raise CursorConflictError(
                f"cursor conflict for {channel_id}: expected {expected_message_id}, got {current}"
            )
        if current is not None and _message_id_value(new_message_id) <= _message_id_value(current):
            raise ValueError("new Telegram cursor must be greater than the current cursor")
        self._cursors[channel_id] = new_message_id


class TelegramAgentPoller:
    """Poll configured TelegramAgent retrievers without performing inference."""

    def __init__(
        self,
        *,
        retrievers: Mapping[str, TelegramAgentAPI],
        cursor_store: TelegramCursorStore,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._retrievers = dict(retrievers)
        self._cursor_store = cursor_store
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    async def poll_once(self, config: TelegramAgentChannelConfig) -> TelegramAgentPollBatch:
        retriever = self._retrievers[config.channel_id]
        if retriever.telegram_chat_id != config.telegram_chat_id:
            raise ValueError(
                f"Telegram chat mismatch for {config.channel_id}: "
                f"configured {config.telegram_chat_id}, retriever {retriever.telegram_chat_id}"
            )

        previous_cursor = await self._cursor_store.load(config.channel_id)
        retrieved = await retriever.retrieve_messages(
            messages_since=previous_cursor,
            maximum_messages=config.maximum_messages,
        )
        messages = sorted(retrieved.messages, key=lambda message: _message_id_value(message.id))
        if previous_cursor is not None:
            previous_value = _message_id_value(previous_cursor)
            messages = [message for message in messages if _message_id_value(message.id) > previous_value]

        observed_at = self._clock()
        envelopes = [
            normalize_telegram_agent_message(
                message,
                channel_id=config.channel_id,
                telegram_chat_id=config.telegram_chat_id,
                retrieval_cursor=previous_cursor,
                observed_at=observed_at,
            )
            for message in messages
        ]
        next_cursor = messages[-1].id if messages else previous_cursor
        return TelegramAgentPollBatch(
            channel_id=config.channel_id,
            telegram_chat_id=config.telegram_chat_id,
            previous_cursor=previous_cursor,
            next_cursor=next_cursor,
            messages=envelopes,
        )

    async def commit(self, batch: TelegramAgentPollBatch) -> None:
        """Advance after the caller durably stores every message in the batch."""
        if batch.next_cursor is None or batch.next_cursor == batch.previous_cursor:
            return
        await self._cursor_store.advance(
            batch.channel_id,
            expected_message_id=batch.previous_cursor,
            new_message_id=batch.next_cursor,
        )


def _message_id_value(message_id: str) -> int:
    try:
        return int(message_id)
    except ValueError as exc:
        raise ValueError(f"Telegram message id must be numeric: {message_id}") from exc
