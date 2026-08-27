"""Compatibility surface for retrieval-only Telegram ingestion."""

from agentic_perp_trading_bot.telegram_ingestion.agent_worker import (
    CallableTelegramAgentRetriever,
    TelegramAgentPoller,
)
from agentic_perp_trading_bot.telegram_ingestion.normalizer import (
    attach_archived_media,
    normalize_telegram_agent_message,
)
from agentic_perp_trading_bot.telegram_ingestion.pipeline import TelegramIngestionPipeline
from agentic_perp_trading_bot.telegram_ingestion.reply_tree import (
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
