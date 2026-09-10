"""Retrieval-only TelegramAgent interface.

File mappings:
``agent_interfaces/telegram.py`` <- ``frameworkless_app/skills_api/telegram_agent.py``;
``skills_api/telegram_agent.py`` <- ``frameworkless_app/skills_api/telegram_agent.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from typing import Protocol

from crewai_app.domain.contracts.schemas import TelegramAgentRetrievalBatch


class TelegramAgentAPI(Protocol):
    """Retrieval-only contract for one configured Telegram chat."""

    telegram_chat_id: str

    async def retrieve_messages(
        self,
        *,
        maximum_messages: int | None,
    ) -> TelegramAgentRetrievalBatch: ...

__all__ = ["TelegramAgentAPI"]
