"""Normalized TelegramAgent handoff to storage and AWS Bedrock boundaries."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from agentic_perp_trading_bot.schemas import (
    TelegramAgentChannelConfig,
    TelegramIngestionRecord,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradeThreadCursor,
)
from agentic_perp_trading_bot.telegram_ingestion.agent_worker import TelegramAgentPoller
from agentic_perp_trading_bot.telegram_ingestion.deduplication import (
    InMemoryTelegramDeduplicator,
)
from agentic_perp_trading_bot.telegram_ingestion.reply_tree import (
    InMemoryReplyTreeStore,
    ReplyTreeStore,
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


class TradeCursorResolver(Protocol):
    async def resolve_for_message(
        self,
        message: TelegramMessageEnvelope,
    ) -> list[TradeThreadCursor]: ...


class TelegramIngestionPipeline:
    """Persist, publish, and acknowledge each TelegramAgent message."""

    def __init__(
        self,
        *,
        poller: TelegramAgentPoller,
        raw_media_archive: S3RawMediaArchive,
        metadata_repository: DynamoDBMessageMetadataRepository,
        bedrock_publisher: BedrockInputPublisher,
        input_deduplicator: InMemoryTelegramDeduplicator | None = None,
        reply_tree_store: ReplyTreeStore | None = None,
        trade_cursor_resolver: TradeCursorResolver | None = None,
    ) -> None:
        self._poller = poller
        self._raw_media_archive = raw_media_archive
        self._metadata_repository = metadata_repository
        self._bedrock_publisher = bedrock_publisher
        self._input_deduplicator = input_deduplicator or InMemoryTelegramDeduplicator()
        self._reply_tree_store = reply_tree_store or InMemoryReplyTreeStore()
        self._trade_cursor_resolver = trade_cursor_resolver

    async def process_once(self, config: TelegramAgentChannelConfig) -> list[TelegramMessageEnvelope]:
        batch = await self._poller.poll_once(config)
        published: list[TelegramMessageEnvelope] = []

        for message in batch.messages:
            contextualized_message = await self._resolve_parent_messages(message)
            archived_message = await self._raw_media_archive.archive(contextualized_message)
            deduplication = self._input_deduplicator.check(archived_message)
            await self._metadata_repository.put(
                TelegramIngestionRecord(
                    message=archived_message,
                    input_deduplication=deduplication,
                )
            )
            await self._reply_tree_store.add(archived_message)
            if deduplication.is_duplicate:
                await self._poller.commit_message(archived_message)
                continue
            context = await self._reply_tree_store.prompt_context_for(
                archived_message
            )
            if self._trade_cursor_resolver is not None:
                context = context.model_copy(
                    update={
                        "active_trade_cursors": (
                            await self._trade_cursor_resolver.resolve_for_message(
                                archived_message
                            )
                        )
                    }
                )
            await self._bedrock_publisher.publish(context)
            published.append(archived_message)
            await self._poller.commit_message(archived_message)

        return published

    async def _resolve_parent_messages(
        self,
        message: TelegramMessageEnvelope,
    ) -> TelegramMessageEnvelope:
        parent_messages = await self._reply_tree_store.parent_messages_for(message)
        return TelegramMessageEnvelope.model_validate(
            {**message.model_dump(), "parent_messages": parent_messages}
        )
