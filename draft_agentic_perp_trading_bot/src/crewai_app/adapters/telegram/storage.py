"""Storage contracts for the Lightsail TelegramAgent ingestion service.

File mappings:
``adapters/telegram/storage.py`` <- ``frameworkless_app/telegram_ingestion/storage.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import List, Protocol

from crewai_app.domain.contracts.schemas import (
    TelegramIngestionRecord,
    TelegramMessageEnvelope,
)


class S3RawMediaArchive(Protocol):
    async def archive(self, message: TelegramMessageEnvelope) -> TelegramMessageEnvelope: ...


class DynamoDBMessageMetadataRepository(Protocol):
    async def put(self, record: TelegramIngestionRecord) -> None: ...


class TelegramMessageReceiptStore(Protocol):
    """Durable per-message processing receipts keyed by channel and message ID."""

    async def contains(self, channel_id: str, telegram_message_id: str) -> bool: ...

    async def record(self, channel_id: str, telegram_message_id: str) -> None: ...


class InMemoryRawMediaArchive:
    """Test adapter; production code should archive media in S3."""

    async def archive(self, message: TelegramMessageEnvelope) -> TelegramMessageEnvelope:
        return message


class InMemoryMessageMetadataRepository:
    """Test adapter; production code should persist records in DynamoDB."""

    def __init__(self) -> None:
        self.records: List[TelegramIngestionRecord] = []

    async def put(self, record: TelegramIngestionRecord) -> None:
        self.records.append(record)


class InMemoryTelegramMessageReceiptStore:
    """Process-local receipt store used by tests and local scaffold runs."""

    def __init__(self, receipts: Mapping[str, Iterable[str]] | None = None) -> None:
        self._receipts = {
            channel_id: set(message_ids)
            for channel_id, message_ids in (receipts or {}).items()
        }

    async def contains(self, channel_id: str, telegram_message_id: str) -> bool:
        return telegram_message_id in self._receipts.get(channel_id, set())

    async def record(self, channel_id: str, telegram_message_id: str) -> None:
        self._receipts.setdefault(channel_id, set()).add(telegram_message_id)


__all__ = [
    "DynamoDBMessageMetadataRepository",
    "InMemoryMessageMetadataRepository",
    "InMemoryRawMediaArchive",
    "InMemoryTelegramMessageReceiptStore",
    "S3RawMediaArchive",
    "TelegramMessageReceiptStore",
]
