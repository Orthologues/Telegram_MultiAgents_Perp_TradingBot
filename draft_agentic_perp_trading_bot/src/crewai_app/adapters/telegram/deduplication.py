"""Multimodal Telegram input deduplication.

The production implementation should persist keys in DynamoDB or another shared
store so TelegramAgent workers deduplicate across processes and restarts.

File mappings:
``adapters/telegram/deduplication.py`` <-
``frameworkless_app/telegram_ingestion/deduplication.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from crewai_app.domain.contracts.schemas import (
    DeduplicationDecision,
    DeduplicationScope,
    TelegramMessageEnvelope,
)


def build_input_dedup_key(message: TelegramMessageEnvelope) -> str:
    text_hash = message.content_hash or "no_text"
    if message.media_hashes:
        media_hashes = ",".join(sorted(message.media_hashes))
    elif message.raw_media_present:
        source_chat = message.telegram_chat_id or message.channel_id
        media_hashes = f"unhydrated:{source_chat}:{message.telegram_message_id}"
    else:
        media_hashes = "no_media"
    return f"{message.owner_id}:{message.channel_id}:{text_hash}:{media_hashes}"


class InMemoryTelegramDeduplicator:
    """Process-local delivery index for duplicate multimodal Telegram inputs.

    ``inspect`` is intentionally non-mutating. A key becomes delivered only
    after the pipeline has published its prompt context successfully.
    """

    def __init__(self) -> None:
        self._seen_keys: set[str] = set()

    def inspect(self, message: TelegramMessageEnvelope) -> DeduplicationDecision:
        dedup_key = message.dedup_key or build_input_dedup_key(message)
        is_duplicate = dedup_key in self._seen_keys
        return DeduplicationDecision(
            scope=DeduplicationScope.MULTIMODAL_INPUT,
            is_duplicate=is_duplicate,
            dedup_key=dedup_key,
            matched_key=dedup_key if is_duplicate else None,
            reasons=["duplicate multimodal Telegram input"] if is_duplicate else [],
        )

    def mark_delivered(self, message: TelegramMessageEnvelope) -> None:
        """Record successful downstream delivery for a normalized message."""
        self._seen_keys.add(message.dedup_key or build_input_dedup_key(message))

    def check(self, message: TelegramMessageEnvelope) -> DeduplicationDecision:
        """Compatibility helper with the historical check-and-mark behavior."""
        decision = self.inspect(message)
        if not decision.is_duplicate:
            self.mark_delivered(message)
        return decision


__all__ = ["InMemoryTelegramDeduplicator", "build_input_dedup_key"]
