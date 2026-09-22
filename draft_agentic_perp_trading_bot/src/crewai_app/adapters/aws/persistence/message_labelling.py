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
    RagCurationSubmission,
    TelegramPromptContext,
    TradingMessageRelationDecision,
)
from crewai_app.domain.policies.rag_curation import RagCurationPolicy


class MessageLabellingRepository(Protocol):
    async def put(self, record: QwenRagLabellingRecord) -> None:
        """Persist a new pending labelling record.

        Args:
            `record`: A ``QwenRagLabellingRecord`` whose status is
                ``"pending"``.

        Returns:
            `None` after `record` has been persisted successfully.

        Raises:
            ValueError: If `record` is not pending or would overwrite an
                existing record in an in-memory implementation.
        """
        ...

    async def transition(
        self,
        record: QwenRagLabellingRecord,
        *,
        expected_status: str,
    ) -> None:
        """Atomically persist a status transition for an existing record.

        Args:
            `record`: The updated labelling record. The status in `record` must
                be the intended next status.
            `expected_status`: The status in `record` before the transition;
                supported values are ``"pending"`` and ``"completed"``.

        Returns:
            `None` after the guarded update succeeds. Repeating the same
            transition is idempotent.

        Raises:
            ValueError: If `expected_status` is unsupported, `record` is
                missing, or its stored status has changed.
        """
        ...


class DynamoDBTable(Protocol):
    def put_item(
        self,
        *,
        Item: Mapping[str, Any],
        **kwargs: Any,
    ) -> Mapping[str, Any]: ...

    def update_item(
        self,
        *,
        Key: Mapping[str, Any],
        UpdateExpression: str,
        ConditionExpression: str,
        ExpressionAttributeValues: Mapping[str, Any],
        ReturnValues: str,
    ) -> Mapping[str, Any]: ...


class DynamoDBMessageLabellingRepository(MessageLabellingRepository):
    """Store deferred labelling records in an injected DynamoDB table."""

    def __init__(self, table: DynamoDBTable) -> None:
        self._table = table

    async def put(self, record: QwenRagLabellingRecord) -> None:
        if record.labelling_status != "pending":
            raise ValueError("completed records must use transition, not put")
        await asyncio.to_thread(
            self._table.put_item,
            Item=_dynamodb_item(record),
            ConditionExpression=(
                "attribute_not_exists(owner_channel_id) "
                "AND attribute_not_exists(telegram_message_id)"
            ),
        )

    async def transition(
        self,
        record: QwenRagLabellingRecord,
        *,
        expected_status: str,
    ) -> None:
        if expected_status not in {"pending", "completed"}:
            raise ValueError("transitions must originate from pending or completed")
        await asyncio.to_thread(
            self._table.update_item,
            Key=_dynamodb_key(record),
            UpdateExpression="SET labelling_status = :status, payload = :payload",
            ConditionExpression="labelling_status = :expected_status",
            ExpressionAttributeValues={
                ":status": record.labelling_status,
                ":expected_status": expected_status,
                ":payload": _dynamodb_payload(record),
            },
            ReturnValues="NONE",
        )


class InMemoryMessageLabellingRepository(MessageLabellingRepository):
    """Process-local adapter for tests and the non-live scaffold."""

    def __init__(self) -> None:
        self.records: dict[tuple[str, str, str], QwenRagLabellingRecord] = {}

    async def put(self, record: QwenRagLabellingRecord) -> None:
        if record.labelling_status != "pending":
            raise ValueError("completed records must use transition, not put")
        message = record.prompt_context.current_message
        key = (
            message.owner_id.value,
            message.channel_id,
            message.telegram_message_id,
        )
        existing = self.records.get(key)
        if existing is not None:
            if existing == record:
                return
            raise ValueError("a labelling record cannot overwrite existing data")
        self.records[key] = record.model_copy(deep=True)

    async def transition(
        self,
        record: QwenRagLabellingRecord,
        *,
        expected_status: str,
    ) -> None:
        message = record.prompt_context.current_message
        key = (message.owner_id.value, message.channel_id, message.telegram_message_id)
        existing = self.records.get(key)
        if existing is None:
            raise ValueError("cannot transition a missing labelling record")
        if existing.labelling_status != expected_status:
            if existing == record:
                return
            raise ValueError(
                "labelling record status changed before the requested transition"
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

    async def complete_after_review(
        self,
        record: QwenRagLabellingRecord,
        submission: RagCurationSubmission,
    ) -> QwenRagLabellingRecord:
        """Validate and persist a human-reviewed completed record."""
        completed = RagCurationPolicy.complete_record(record, submission)
        await self._repository.transition(completed, expected_status="pending")
        return completed

    async def promote_after_review(
        self,
        record: QwenRagLabellingRecord,
    ) -> QwenRagLabellingRecord:
        """Validate and persist promotion of a completed record into RAG."""
        promoted = RagCurationPolicy.promote_record(record)
        await self._repository.transition(promoted, expected_status="completed")
        return promoted


def _dynamodb_key(record: QwenRagLabellingRecord) -> dict[str, str]:
    message = record.prompt_context.current_message
    return {
        "owner_channel_id": f"{message.owner_id.value}#{message.channel_id}",
        "telegram_message_id": message.telegram_message_id,
    }


def _dynamodb_payload(record: QwenRagLabellingRecord) -> dict[str, Any]:
    return json.loads(record.model_dump_json(), parse_float=Decimal)


def _dynamodb_item(record: QwenRagLabellingRecord) -> dict[str, Any]:
    return {
        **_dynamodb_key(record),
        "queued_at": record.queued_at.isoformat(),
        "labelling_status": record.labelling_status,
        "payload": _dynamodb_payload(record),
    }


__all__ = [
    "DeferredQwenLabellingQueue",
    "DynamoDBMessageLabellingRepository",
    "DynamoDBTable",
    "InMemoryMessageLabellingRepository",
    "MessageLabellingRepository",
]
