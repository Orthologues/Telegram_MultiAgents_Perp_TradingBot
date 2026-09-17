"""Deferred QWEN message labelling persisted for later RAG curation."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from crewai_app.domain.contracts.schemas import (
    QwenRagLabellingRecord,
    TelegramPromptContext,
    TradingMessageRelationDecision,
)


class MessageLabellingRepository(Protocol):
    async def put(self, record: QwenRagLabellingRecord) -> None: ...


class DynamoDBTable(Protocol):
    def put_item(self, *, Item: Mapping[str, Any]) -> Mapping[str, Any]: ...


class DynamoDBMessageLabellingRepository:
    """Store deferred labelling records in an injected DynamoDB table."""

    def __init__(self, table: DynamoDBTable) -> None:
        self._table = table

    async def put(self, record: QwenRagLabellingRecord) -> None:
        message = record.prompt_context.current_message
        payload = json.loads(record.model_dump_json(), parse_float=Decimal)
        item = {
            "owner_channel_id": f"{message.owner_id.value}#{message.channel_id}",
            "telegram_message_id": message.telegram_message_id,
            "queued_at": record.queued_at.isoformat(),
            "labelling_status": record.labelling_status,
            "payload": payload,
        }
        await asyncio.to_thread(self._table.put_item, Item=item)


class InMemoryMessageLabellingRepository:
    """Process-local adapter for tests and the non-live scaffold."""

    def __init__(self) -> None:
        self.records: dict[tuple[str, str, str], QwenRagLabellingRecord] = {}

    async def put(self, record: QwenRagLabellingRecord) -> None:
        message = record.prompt_context.current_message
        key = (
            message.owner_id.value,
            message.channel_id,
            message.telegram_message_id,
        )
        self.records[key] = record.model_copy(deep=True)


class DeferredQwenLabellingQueue:
    """Queue flagged QWEN relation outputs without blocking live ingestion."""

    def __init__(
        self,
        repository: MessageLabellingRepository,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))

    async def enqueue_if_needed(
        self,
        prompt_context: TelegramPromptContext,
        relation_decision: TradingMessageRelationDecision,
    ) -> QwenRagLabellingRecord | None:
        if not relation_decision.needs_human_labelling:
            return None
        record = QwenRagLabellingRecord(
            prompt_context=prompt_context,
            relation_decision=relation_decision,
            queued_at=self._clock(),
        )
        await self._repository.put(record)
        return record


__all__ = [
    "DeferredQwenLabellingQueue",
    "DynamoDBMessageLabellingRepository",
    "DynamoDBTable",
    "InMemoryMessageLabellingRepository",
    "MessageLabellingRepository",
]
