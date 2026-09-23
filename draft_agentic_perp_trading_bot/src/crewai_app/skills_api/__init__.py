"""Legacy skill-API compatibility surface.

Canonical CrewAI responsibility protocols are exported from
crewai_app.agent_interfaces. The names below remain import-compatible for the
retained frameworkless_app comparison path; deterministic policies are
implemented under domain.policies and tools.

File mappings:
``skills_api/{__init__,ministral_filter/interfaces,omitted_stop_loss_inference/interfaces,owner_qwen/interfaces,qwen_agent_rag_loading/interfaces}.py``
<- ``frameworkless_app/skills_api/{__init__,ministral_filter,omitted_stop_loss_inference,owner_qwen,qwen_agent_rag_loading,telegram_agent}.py``;
``domain/contracts/__init__.py`` <- ``frameworkless_app/schemas.py``.
"""

from crewai_app.skills_api.ministral_filter import MinistralFilterAPI
from crewai_app.skills_api.omitted_stop_loss_inference import (
    OmittedStopLossInferenceAPI,
)
from crewai_app.skills_api.owner_qwen import OwnerQwenAPI
from crewai_app.skills_api.qwen_agent_rag_loading import QwenAgentRagLoadingAPI
from crewai_app.agent_interfaces.telegram import TelegramAgentAPI

__all__ = [
    "MinistralFilterAPI",
    "OmittedStopLossInferenceAPI",
    "OwnerQwenAPI",
    "QwenAgentRagLoadingAPI",
    "TelegramAgentAPI",
]
