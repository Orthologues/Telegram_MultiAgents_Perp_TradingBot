"""Retrieval-only TelegramAgent skill API."""

from __future__ import annotations

from typing import Protocol

from agentic_perp_trading_bot.schemas import TelegramAgentRetrievalBatch


class TelegramAgentAPI(Protocol):
    telegram_chat_id: str

    async def retrieve_messages(
        self,
        *,
        messages_since: str | None,
        maximum_messages: int | None,
    ) -> TelegramAgentRetrievalBatch: ...
