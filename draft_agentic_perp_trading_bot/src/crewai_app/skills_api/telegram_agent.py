"""Retrieval-only TelegramAgent skill API.

File mappings:
``skills_api/telegram_agent.py`` <- ``frameworkless_app/skills_api/telegram_agent.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

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
