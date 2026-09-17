"""Telegram provenance and serial-RAG contracts.

File mappings:
``domain/contracts/telegram.py`` <- ``frameworkless_app/schemas.py``;
``domain/contracts/definitions.py`` <- ``frameworkless_app/schemas.py``.
"""

from crewai_app.domain.contracts.definitions import (
    AssetGroup,
    DeduplicationDecision,
    DeduplicationScope,
    IngestionTransport,
    OwnerId,
    OwnerRagProfile,
    QwenRagLabellingRecord,
    SerialRagExample,
    TelegramAgentChannelConfig,
    TelegramAgentPollBatch,
    TelegramAgentRetrievalBatch,
    TelegramAgentRetrievedMessage,
    TelegramIngestionRecord,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TelegramPromptMessage,
    TelegramRagMessageReference,
    TradingMessageRelation,
    TradingMessageRelationDecision,
)

__all__ = [
    "AssetGroup",
    "DeduplicationDecision",
    "DeduplicationScope",
    "IngestionTransport",
    "OwnerId",
    "OwnerRagProfile",
    "QwenRagLabellingRecord",
    "SerialRagExample",
    "TelegramAgentChannelConfig",
    "TelegramAgentPollBatch",
    "TelegramAgentRetrievalBatch",
    "TelegramAgentRetrievedMessage",
    "TelegramIngestionRecord",
    "TelegramMessageEnvelope",
    "TelegramPromptContext",
    "TelegramPromptMessage",
    "TelegramRagMessageReference",
    "TradingMessageRelation",
    "TradingMessageRelationDecision",
]
