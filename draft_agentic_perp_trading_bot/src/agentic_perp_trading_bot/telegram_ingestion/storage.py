"""Storage contracts for the Lightsail TelegramAgent ingestion service."""

from __future__ import annotations

from typing import Protocol

from agentic_perp_trading_bot.schemas import (
    TelegramIngestionRecord,
    TelegramMessageEnvelope,
)


class S3RawMediaArchive(Protocol):
    async def archive(self, message: TelegramMessageEnvelope) -> TelegramMessageEnvelope: ...


class DynamoDBMessageMetadataRepository(Protocol):
    async def put(self, record: TelegramIngestionRecord) -> None: ...


class InMemoryRawMediaArchive:
    """Test adapter; production code should archive media in S3."""

    async def archive(self, message: TelegramMessageEnvelope) -> TelegramMessageEnvelope:
        return message


class InMemoryMessageMetadataRepository:
    """Test adapter; production code should persist records in DynamoDB."""

    def __init__(self) -> None:
        self.records: list[TelegramIngestionRecord] = []

    async def put(self, record: TelegramIngestionRecord) -> None:
        self.records.append(record)
