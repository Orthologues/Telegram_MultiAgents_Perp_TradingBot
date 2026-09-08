"""Retrieval-only TelegramAgent skill API.

Predecessor: ``src/frameworkless_app/skills_api/telegram_agent.py``. The
retrieval-batch contract still originates in ``src/frameworkless_app/schemas.py``
through the CrewAI contract facade.
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
