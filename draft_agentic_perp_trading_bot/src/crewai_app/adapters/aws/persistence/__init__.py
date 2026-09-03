"""S3, DynamoDB, and ElastiCache compatibility surfaces."""

from frameworkless_app.performance_engine.history import (
    DynamoDBExecutionHistoryRepository,
    InMemoryExecutionHistoryRepository,
)
from frameworkless_app.telegram_ingestion.reply_tree import (
    ElastiCacheReplyTreeStore,
    InMemoryReplyTreeStore,
    ReplyTreeStore,
)
from frameworkless_app.telegram_ingestion.storage import (
    DynamoDBMessageMetadataRepository,
    InMemoryMessageMetadataRepository,
    InMemoryRawMediaArchive,
    InMemoryTelegramMessageReceiptStore,
    S3RawMediaArchive,
    TelegramMessageReceiptStore,
)
from frameworkless_app.trade_cursor import (
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
