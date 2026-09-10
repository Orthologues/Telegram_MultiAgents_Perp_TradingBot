"""Compatibility re-export for the canonical retrieval-only Telegram API.

File mappings:
``skills_api/telegram_agent.py`` <- ``frameworkless_app/skills_api/telegram_agent.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from crewai_app.agent_interfaces.telegram import TelegramAgentAPI  # noqa: F401

__all__ = ["TelegramAgentAPI"]
