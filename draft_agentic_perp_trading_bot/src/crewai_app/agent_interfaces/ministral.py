"""Shared Ministral review interface.

Predecessor: ``src/frameworkless_app/skills_api/ministral_filter.py``.
Contract types remain exposed through ``crewai_app.domain.contracts.schemas``,
whose legacy definitions are still in ``src/frameworkless_app/schemas.py``.
"""

from crewai_app.skills_api.ministral_filter import MinistralFilterAPI

__all__ = ["MinistralFilterAPI"]
