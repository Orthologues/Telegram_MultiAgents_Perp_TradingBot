"""Telegram provenance and serial-RAG contract compatibility surface."""

from frameworkless_app.schemas import (
    AssetGroup,
    DeduplicationDecision,
    DeduplicationScope,
    IngestionTransport,
    OwnerId,
    OwnerRagProfile,
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
)

__all__ = [
    "AssetGroup",
    "DeduplicationDecision",
    "DeduplicationScope",
    "IngestionTransport",
    "OwnerId",
    "OwnerRagProfile",
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
]
