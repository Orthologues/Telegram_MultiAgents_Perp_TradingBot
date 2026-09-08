"""Retrieval-only TelegramAgent interface.

File mappings:
``agent_interfaces/telegram.py`` <- ``frameworkless_app/skills_api/telegram_agent.py``;
``skills_api/telegram_agent.py`` <- ``frameworkless_app/skills_api/telegram_agent.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from crewai_app.skills_api.telegram_agent import TelegramAgentAPI

__all__ = ["TelegramAgentAPI"]
