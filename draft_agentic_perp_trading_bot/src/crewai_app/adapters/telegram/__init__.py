"""Compatibility surface for retrieval-only Telegram ingestion."""

from frameworkless_app.telegram_ingestion.agent_worker import (
    CallableTelegramAgentRetriever,
    TelegramAgentPoller,
)
from frameworkless_app.telegram_ingestion.normalizer import (
    attach_archived_media,
    normalize_telegram_agent_message,
)
from frameworkless_app.telegram_ingestion.pipeline import TelegramIngestionPipeline
from frameworkless_app.telegram_ingestion.reply_tree import (
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
