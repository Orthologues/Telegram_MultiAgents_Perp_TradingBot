import asyncio
from datetime import UTC, datetime

import pytest

from crewai_app.adapters.aws.persistence.message_labelling import (
    DeferredQwenLabellingQueue,
    InMemoryMessageLabellingRepository,
)
from crewai_app.domain.contracts import (
    AssetGroup,
    OwnerId,
    QwenRagLabellingRecord,
    RagCurationSubmission,
    SerialRagExample,
    StrategyTier,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TelegramPromptMessage,
    TelegramRagMessageReference,
    TradingMessageRelation,
    TradingMessageRelationDecision,
)
from crewai_app.domain.policies.rag_curation import (
    RagCurationPolicy,
    validated_serial_rag_examples,
)

NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def _record() -> QwenRagLabellingRecord:
    message = TelegramMessageEnvelope(
        owner_id=OwnerId.OWNER_A_SHU_QIN,
        channel_id="owner_a_channel_a",
        asset_group=AssetGroup.MIXED,
        telegram_message_id="103",
        received_at=NOW,
        parent_messages=["101", "102"],
        raw_text="ETH 多",
    )
    context = TelegramPromptContext.from_message(
        message,
        [
            TelegramPromptMessage(telegram_message_id="101", raw_text="parent 1"),
            TelegramPromptMessage(telegram_message_id="102", raw_text="parent 2"),
        ],
    )
    decision = TradingMessageRelationDecision(
        owner_id=message.owner_id,
        channel_id=message.channel_id,
        telegram_message_id=message.telegram_message_id,
        relation=TradingMessageRelation.AMBIGUOUS,
        confidence=0.2,
    )
    return QwenRagLabellingRecord(
        prompt_context=context,
        relation_decision=decision,
        queued_at=NOW,
    )


def _submission(record: QwenRagLabellingRecord) -> RagCurationSubmission:
    message = record.prompt_context.current_message
    return RagCurationSubmission(
        owner_id=message.owner_id,
        channel_id=message.channel_id,
        telegram_message_id=message.telegram_message_id,
        serial_rag_example=SerialRagExample(
            example_id="owner-a-eth-001",
            strategy_tier=StrategyTier.INTERMEDIATE,
            messages=[
                TelegramRagMessageReference(
                    telegram_message_id=message_id,
                    telegram_message_url=f"https://t.me/c/123/{message_id}",
                )
                for message_id in ("101", "102", "103")
            ],
            s3_archive_uri="s3://private-rag-bucket/owner-a-eth-001.json",
            execution_label="ambiguous",
        ),
        reviewed_by="human-reviewer",
        reviewed_at=NOW,
        provenance_verified=True,
    )


def test_curation_requires_complete_verified_provenance_before_promotion() -> None:
    record = _record()

    completed = RagCurationPolicy.complete_record(record, _submission(record))

    assert completed.labelling_status == "completed"
    assert completed.curated_example is not None
    assert completed.curated_example.validation is not None
    assert validated_serial_rag_examples([completed.curated_example]) == [
        completed.curated_example
    ]

    promoted = RagCurationPolicy.promote_record(completed)

    assert promoted.labelling_status == "promoted"


def test_curation_rejects_unverified_or_incomplete_submissions() -> None:
    record = _record()
    submission = _submission(record)

    with pytest.raises(ValueError, match="verified"):
        RagCurationPolicy.complete_record(
            record,
            submission.model_copy(update={"provenance_verified": False}),
        )

    incomplete_example = submission.serial_rag_example.model_copy(
        update={"messages": submission.serial_rag_example.messages[1:]}
    )
    with pytest.raises(ValueError, match="missing prompt message IDs"):
        RagCurationPolicy.complete_record(
            record,
            submission.model_copy(update={"serial_rag_example": incomplete_example}),
        )


def test_unvalidated_examples_are_excluded_from_rag_loaders() -> None:
    record = _record()
    completed = RagCurationPolicy.complete_record(record, _submission(record))
    assert completed.curated_example is not None

    assert validated_serial_rag_examples(
        [
            _submission(record).serial_rag_example,
            completed.curated_example,
        ]
    ) == [completed.curated_example]


def test_labelling_repository_guards_pending_to_completed_transitions() -> None:
    record = _record()
    repository = InMemoryMessageLabellingRepository()
    queue = DeferredQwenLabellingQueue(repository)
    asyncio.run(repository.put(record))

    completed = asyncio.run(queue.complete_after_review(record, _submission(record)))
    promoted = asyncio.run(queue.promote_after_review(completed))
    assert promoted.labelling_status == "promoted"

    key = (
        record.prompt_context.current_message.owner_id.value,
        record.prompt_context.current_message.channel_id,
        record.prompt_context.current_message.telegram_message_id,
    )
    assert repository.records[key].labelling_status == "promoted"
    with pytest.raises(ValueError, match="cannot overwrite"):
        asyncio.run(repository.put(record))
