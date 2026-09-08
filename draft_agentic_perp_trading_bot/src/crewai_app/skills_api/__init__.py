"""Public API contracts for CrewAI agent-owned skills.

These APIs replace the corresponding contracts under
``src/frameworkless_app/skills_api``. Their domain and execution types still
resolve through the legacy definitions in ``src/frameworkless_app/schemas.py``.
"""

from crewai_app.skills_api.ministral_filter import MinistralFilterAPI
from crewai_app.skills_api.omitted_stop_loss_inference import (
    OmittedStopLossInferenceAPI,
)
from crewai_app.skills_api.owner_qwen import OwnerQwenAPI
from crewai_app.skills_api.qwen_agent_rag_loading import QwenAgentRagLoadingAPI
from crewai_app.skills_api.telegram_agent import TelegramAgentAPI

__all__ = [
    "MinistralFilterAPI",
    "OmittedStopLossInferenceAPI",
    "OwnerQwenAPI",
    "QwenAgentRagLoadingAPI",
    "TelegramAgentAPI",
]
