"""S3, DynamoDB, and ElastiCache compatibility surfaces."""

from agentic_perp_trading_bot.performance_engine.history import (
    DynamoDBExecutionHistoryRepository,
    InMemoryExecutionHistoryRepository,
)
from agentic_perp_trading_bot.telegram_ingestion.reply_tree import (
    ElastiCacheReplyTreeStore,
    InMemoryReplyTreeStore,
    ReplyTreeStore,
)
from agentic_perp_trading_bot.telegram_ingestion.storage import (
    DynamoDBMessageMetadataRepository,
    InMemoryMessageMetadataRepository,
    InMemoryRawMediaArchive,
    InMemoryTelegramMessageReceiptStore,
    S3RawMediaArchive,
    TelegramMessageReceiptStore,
)
from agentic_perp_trading_bot.trade_cursor import (
    DynamoDBTradeCursorRepository,
    InMemoryTradeCursorRepository,
)
from crewai_app.adapters.aws.persistence.context_loaders import (
    LocalOwnerProfileRagLoader,
    ReplyTreeParentContextLoader,
    TradeCursorContextLoader,
)
from crewai_app.adapters.aws.persistence.decision_repository import (
    InMemoryDecisionRepository,
)

__all__ = [
    "DynamoDBExecutionHistoryRepository",
    "DynamoDBMessageMetadataRepository",
    "DynamoDBTradeCursorRepository",
    "ElastiCacheReplyTreeStore",
    "InMemoryExecutionHistoryRepository",
    "InMemoryDecisionRepository",
    "InMemoryMessageMetadataRepository",
    "InMemoryRawMediaArchive",
    "InMemoryReplyTreeStore",
    "InMemoryTelegramMessageReceiptStore",
    "InMemoryTradeCursorRepository",
    "ReplyTreeStore",
    "LocalOwnerProfileRagLoader",
    "ReplyTreeParentContextLoader",
    "S3RawMediaArchive",
    "TelegramMessageReceiptStore",
    "TradeCursorContextLoader",
]
