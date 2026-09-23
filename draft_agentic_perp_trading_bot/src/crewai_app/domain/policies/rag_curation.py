"""Validation boundary for promoting deferred QWEN labels into serial RAG."""

from __future__ import annotations

from collections.abc import Iterable

from crewai_app.domain.contracts.schemas import (
    QwenRagLabellingRecord,
    RagCurationSubmission,
    RagValidationMetadata,
    SerialRagExample,
)


class RagCurationPolicy:
    """Validate human labels and provenance before RAG promotion."""

    @staticmethod
    def complete_record(
        record: QwenRagLabellingRecord,
        submission: RagCurationSubmission,
    ) -> QwenRagLabellingRecord:
        if record.labelling_status != "pending":
            raise ValueError("only pending labelling records can be completed")

        source = record.prompt_context.current_message
        if (
            submission.owner_id,
            submission.channel_id,
            submission.telegram_message_id,
        ) != (
            source.owner_id,
            source.channel_id,
            source.telegram_message_id,
        ):
            raise ValueError("curation submission does not match the labelling record")
        if not submission.provenance_verified:
            raise ValueError("curation requires verified Telegram and archive provenance")

        expected_ids = {
            source.telegram_message_id,
            *(parent.telegram_message_id for parent in record.prompt_context.parent_messages),
        }
        submitted_ids = {
            message.telegram_message_id
            for message in submission.serial_rag_example.messages
        }
        missing_ids = sorted(expected_ids - submitted_ids, key=int)
        if missing_ids:
            raise ValueError(
                "curated serial-RAG example is missing prompt message IDs: "
                f"{missing_ids}"
            )

        validated_example = submission.serial_rag_example.model_copy(
            update={
                "validation": RagValidationMetadata(
                    reviewed_by=submission.reviewed_by,
                    reviewed_at=submission.reviewed_at,
                )
            }
        )
        return record.model_copy(
            update={
                "labelling_status": "completed",
                "curated_example": validated_example,
            }
        )

    @staticmethod
    def promote_record(record: QwenRagLabellingRecord) -> QwenRagLabellingRecord:
        if record.labelling_status != "completed":
            raise ValueError("only completed labelling records can be promoted")
        if record.curated_example is None or record.curated_example.validation is None:
            raise ValueError("promotion requires a validated curated example")
        return record.model_copy(update={"labelling_status": "promoted"})


def validated_serial_rag_examples(
    examples: Iterable[SerialRagExample],
) -> list[SerialRagExample]:
    """Return only examples carrying explicit human validation metadata."""

    return [example for example in examples if example.validation is not None]


__all__ = ["RagCurationPolicy", "validated_serial_rag_examples"]
