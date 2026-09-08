"""Canonical retrieval-only Telegram ingestion adapters.

File mappings:
``adapters/telegram/{__init__,agent_worker,deduplication,normalizer,pipeline,reply_tree,storage}.py``
<- ``frameworkless_app/telegram_ingestion/{__init__,agent_worker,deduplication,normalizer,pipeline,reply_tree,storage}.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from crewai_app.adapters.telegram.agent_worker import (
    CallableTelegramAgentRetriever,
    TelegramAgentPoller,
)
from crewai_app.adapters.telegram.normalizer import (
    attach_archived_media,
    normalize_telegram_agent_message,
)
from crewai_app.adapters.telegram.pipeline import TelegramIngestionPipeline
from crewai_app.adapters.telegram.reply_tree import (
    ElastiCacheReplyTreeStore,
    InMemoryReplyTreeStore,
    ReplyTreeStore,
)

__all__ = [
    "CallableTelegramAgentRetriever",
    "ElastiCacheReplyTreeStore",
    "InMemoryReplyTreeStore",
    "ReplyTreeStore",
    "TelegramAgentPoller",
    "TelegramIngestionPipeline",
    "attach_archived_media",
    "normalize_telegram_agent_message",
]
