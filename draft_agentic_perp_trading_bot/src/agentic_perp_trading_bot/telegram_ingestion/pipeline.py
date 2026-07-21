"""Normalized TelegramAgent handoff to storage and AWS Bedrock boundaries."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from agentic_perp_trading_bot.schemas import (
    TelegramAgentChannelConfig,
    TelegramIngestionRecord,
    TelegramMessageEnvelope,
)
from agentic_perp_trading_bot.telegram_ingestion.agent_worker import TelegramAgentPoller
from agentic_perp_trading_bot.telegram_ingestion.deduplication import (
    InMemoryTelegramDeduplicator,
)
from agentic_perp_trading_bot.telegram_ingestion.storage import (
    DynamoDBMessageMetadataRepository,
    S3RawMediaArchive,
)


class BedrockInputPublisher:
    """Downstream handoff for normalized owner-aware messages."""

    def __init__(self, publish: Callable[[TelegramMessageEnvelope], Awaitable[None]]) -> None:
        self._publish = publish

    async def publish(self, message: TelegramMessageEnvelope) -> None:
        await self._publish(message)


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
    ) -> None:
        self._poller = poller
        self._raw_media_archive = raw_media_archive
        self._metadata_repository = metadata_repository
        self._bedrock_publisher = bedrock_publisher
        self._input_deduplicator = input_deduplicator or InMemoryTelegramDeduplicator()

    async def process_once(self, config: TelegramAgentChannelConfig) -> list[TelegramMessageEnvelope]:
        batch = await self._poller.poll_once(config)
        published: list[TelegramMessageEnvelope] = []

        for message in batch.messages:
            archived_message = await self._raw_media_archive.archive(message)
            deduplication = self._input_deduplicator.check(archived_message)
            await self._metadata_repository.put(
                TelegramIngestionRecord(
                    message=archived_message,
                    input_deduplication=deduplication,
                )
            )
            if deduplication.is_duplicate:
                continue
            await self._bedrock_publisher.publish(archived_message)
            published.append(archived_message)

        await self._poller.commit(batch)
        return published
