"""Shared Ministral review interface.

File mappings:
``agent_interfaces/ministral.py`` <- ``frameworkless_app/skills_api/ministral_filter.py``;
``skills_api/ministral_filter.py`` <- ``frameworkless_app/skills_api/ministral_filter.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from crewai_app.skills_api.ministral_filter import MinistralFilterAPI

__all__ = ["MinistralFilterAPI"]
