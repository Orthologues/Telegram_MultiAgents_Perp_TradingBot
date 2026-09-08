"""Retrieval-only TelegramAgent interface.

Predecessor: ``src/frameworkless_app/skills_api/telegram_agent.py``. Its
retrieval-batch contract is still backed by the legacy schema definitions in
``src/frameworkless_app/schemas.py``.
"""

from crewai_app.skills_api.telegram_agent import TelegramAgentAPI

__all__ = ["TelegramAgentAPI"]
