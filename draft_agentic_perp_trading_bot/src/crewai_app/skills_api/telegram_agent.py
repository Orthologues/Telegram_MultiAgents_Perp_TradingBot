"""Retrieval-only TelegramAgent skill API."""

from __future__ import annotations

from typing import Protocol

from crewai_app.domain.contracts.schemas import TelegramAgentRetrievalBatch


class TelegramAgentAPI(Protocol):
    telegram_chat_id: str

    async def retrieve_messages(
        self,
        *,
        maximum_messages: int | None,
    ) -> TelegramAgentRetrievalBatch: ...
