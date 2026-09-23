"""Compatibility manifest-loader API for the pre-CrewAI QWEN path.

Canonical serial-RAG loading is exposed through agent_interfaces.qwen. It
returns message-scoped examples; this older API returns an owner profile and
remains only for frameworkless comparison callers.

File mappings:
``skills_api/qwen_agent_rag_loading/interfaces.py`` <-
``frameworkless_app/skills_api/qwen_agent_rag_loading.py``;
``domain/contracts/__init__.py`` <- ``frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from typing import Protocol

from crewai_app.agent_interfaces.qwen import SerialRagLoaderAPI
from crewai_app.domain.contracts import OwnerRagProfile


class QwenAgentRagLoadingAPI(Protocol):
    def load_rag_profile(self) -> OwnerRagProfile: ...


__all__ = ["QwenAgentRagLoadingAPI", "SerialRagLoaderAPI"]
