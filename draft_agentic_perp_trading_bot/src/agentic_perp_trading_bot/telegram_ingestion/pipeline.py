"""Normalized TelegramAgent handoff to storage and AWS Bedrock boundaries."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from agentic_perp_trading_bot.schemas import (
    TelegramAgentChannelConfig,
    TelegramIngestionRecord,
    TelegramMessageEnvelope,
    TelegramPromptContext,
)
from agentic_perp_trading_bot.telegram_ingestion.agent_worker import TelegramAgentPoller
from agentic_perp_trading_bot.telegram_ingestion.deduplication import (
    InMemoryTelegramDeduplicator,
)
from agentic_perp_trading_bot.telegram_ingestion.reply_tree import (
    InMemoryReplyTreeIndexRegistry,
)
from agentic_perp_trading_bot.telegram_ingestion.storage import (
    DynamoDBMessageMetadataRepository,
    S3RawMediaArchive,
)


class BedrockInputPublisher:
    """Downstream transfer of source messages and serial prompt context."""

    def __init__(self, publish: Callable[[TelegramPromptContext], Awaitable[None]]) -> None:
        self._publish = publish

    async def publish(self, context: TelegramPromptContext) -> None:
        await self._publish(context)


class TelegramIngestionPipeline:
    """Persist, deduplicate, publish, and then commit one TelegramAgent batch."""

    def __init__(
        self,
        *,
        poller: TelegramAgentPoller,
        raw_media_archive: S3RawMediaArchive,
        metadata_repository: DynamoDBMessageMetadataRepository,
        bedrock_publisher: BedrockInputPublisher,
        input_deduplicator: InMemoryTelegramDeduplicator | None = None,
        reply_tree_indexes: InMemoryReplyTreeIndexRegistry | None = None,
    ) -> None:
        self._poller = poller
        self._raw_media_archive = raw_media_archive
        self._metadata_repository = metadata_repository
        self._bedrock_publisher = bedrock_publisher
        self._input_deduplicator = input_deduplicator or InMemoryTelegramDeduplicator()
        self._reply_tree_indexes = reply_tree_indexes or InMemoryReplyTreeIndexRegistry()

    async def process_once(self, config: TelegramAgentChannelConfig) -> list[TelegramMessageEnvelope]:
        batch = await self._poller.poll_once(config)
        published: list[TelegramMessageEnvelope] = []

        for message in batch.messages:
            contextualized_message = self._resolve_parent_messages(message)
            archived_message = await self._raw_media_archive.archive(contextualized_message)
            deduplication = self._input_deduplicator.check(archived_message)
            await self._metadata_repository.put(
                TelegramIngestionRecord(
                    message=archived_message,
                    input_deduplication=deduplication,
                )
            )
            reply_tree_index = self._reply_tree_indexes.for_owner(archived_message.owner_id)
            reply_tree_index.add(archived_message)
            if deduplication.is_duplicate:
                continue
            await self._bedrock_publisher.publish(
                reply_tree_index.prompt_context_for(archived_message)
            )
            published.append(archived_message)

        await self._poller.commit(batch)
        return published

    def _resolve_parent_messages(
        self,
        message: TelegramMessageEnvelope,
    ) -> TelegramMessageEnvelope:
        parent_messages = self._reply_tree_indexes.for_owner(message.owner_id).parent_messages_for(
            message
        )
        return TelegramMessageEnvelope.model_validate(
            {**message.model_dump(), "parent_messages": parent_messages}
        )
