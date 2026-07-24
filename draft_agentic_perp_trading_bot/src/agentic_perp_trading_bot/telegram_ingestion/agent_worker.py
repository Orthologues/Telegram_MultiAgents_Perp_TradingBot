"""AG2 TelegramAgent polling and per-message receipt boundaries.

AG2's TelegramAgent retrieval tool is pull-based. This scaffold retrieves a
bounded recent window and keeps per-message receipt recording separate from
retrieval so callers can persist media and metadata before acknowledging each
message.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Protocol, Self

from agentic_perp_trading_bot.schemas import (
    TelegramAgentChannelConfig,
    TelegramAgentPollBatch,
    TelegramAgentRetrievalBatch,
    TelegramMessageEnvelope,
)
from agentic_perp_trading_bot.skills_api import TelegramAgentAPI
from agentic_perp_trading_bot.telegram_ingestion.normalizer import (
    normalize_telegram_agent_message,
)
from agentic_perp_trading_bot.telegram_ingestion.storage import TelegramMessageReceiptStore


class TelegramRetrieveCallable(Protocol):
    """Retrieval-only wrapper around one configured AG2 TelegramAgent tool."""

    def __call__(
        self,
        *,
        maximum_messages: int | None,
    ) -> Awaitable[dict[str, Any] | str]: ...


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
        maximum_messages: int | None,
    ) -> TelegramAgentRetrievalBatch:
        payload = await self._retrieve(
            maximum_messages=maximum_messages,
        )
        if not isinstance(payload, dict):
            raise RuntimeError(f"AG2 Telegram retrieval failed: {payload}")

        return TelegramAgentRetrievalBatch.model_validate(
            {**payload, "telegram_chat_id": self.telegram_chat_id}
        )


class TelegramAgentPoller:
    """Poll configured TelegramAgent retrievers without performing inference."""

    def __init__(
        self,
        *,
        retrievers: Mapping[str, TelegramAgentAPI],
        receipt_store: TelegramMessageReceiptStore,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._retrievers = dict(retrievers)
        self._receipt_store = receipt_store
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    async def poll_once(self, config: TelegramAgentChannelConfig) -> TelegramAgentPollBatch:
        retriever = self._retrievers[config.channel_id]
        if retriever.telegram_chat_id != config.telegram_chat_id:
            raise ValueError(
                f"Telegram chat mismatch for {config.channel_id}: "
                f"configured {config.telegram_chat_id}, retriever {retriever.telegram_chat_id}"
            )

        retrieved = await retriever.retrieve_messages(
            maximum_messages=config.maximum_messages,
        )
        messages = sorted(retrieved.messages, key=lambda message: _message_id_value(message.id))
        unacknowledged_messages = []
        observed_message_ids: set[str] = set()
        for message in messages:
            if message.id in observed_message_ids:
                continue
            observed_message_ids.add(message.id)
            if not await self._receipt_store.contains(config.channel_id, message.id):
                unacknowledged_messages.append(message)

        observed_at = self._clock()
        envelopes = [
            normalize_telegram_agent_message(
                message,
                channel_id=config.channel_id,
                telegram_chat_id=config.telegram_chat_id,
                observed_at=observed_at,
            )
            for message in unacknowledged_messages
        ]
        return TelegramAgentPollBatch(
            channel_id=config.channel_id,
            telegram_chat_id=config.telegram_chat_id,
            messages=envelopes,
        )

    async def commit_message(self, message: TelegramMessageEnvelope) -> None:
        """Record one message only after its durable processing succeeds."""
        await self._receipt_store.record(
            message.channel_id,
            message.telegram_message_id,
        )


def _message_id_value(message_id: str) -> int:
    try:
        return int(message_id)
    except ValueError as exc:
        raise ValueError(f"Telegram message id must be numeric: {message_id}") from exc
