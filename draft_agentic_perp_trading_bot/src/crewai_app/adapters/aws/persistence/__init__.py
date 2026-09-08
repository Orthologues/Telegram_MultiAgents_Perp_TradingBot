"""S3, DynamoDB, and ElastiCache persistence boundaries.

File mappings:
``adapters/aws/persistence/history.py`` <-
``frameworkless_app/performance_engine/history.py``;
``adapters/telegram/{reply_tree,storage}.py`` <-
``frameworkless_app/telegram_ingestion/{reply_tree,storage}.py``;
``domain/lifecycle/cursor.py`` <- ``frameworkless_app/trade_cursor.py``.
"""

from crewai_app.adapters.aws.persistence.history import (
    DynamoDBExecutionHistoryRepository,
    InMemoryExecutionHistoryRepository,
)
from crewai_app.adapters.telegram.reply_tree import (
    ElastiCacheReplyTreeStore,
    InMemoryReplyTreeStore,
    ReplyTreeStore,
)
from crewai_app.adapters.telegram.storage import (
    DynamoDBMessageMetadataRepository,
    InMemoryMessageMetadataRepository,
    InMemoryRawMediaArchive,
    InMemoryTelegramMessageReceiptStore,
    S3RawMediaArchive,
    TelegramMessageReceiptStore,
)
from crewai_app.domain.lifecycle.cursor import (
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
