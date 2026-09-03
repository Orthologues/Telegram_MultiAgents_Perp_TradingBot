"""Draft multimodal Telegram input deduplication.

The production implementation should persist keys in DynamoDB or another shared
store so TelegramAgent workers deduplicate across processes and restarts.
"""

from __future__ import annotations

from frameworkless_app.schemas import (
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
    """Process-local placeholder for duplicate Chinese text/image Telegram inputs."""

    def __init__(self) -> None:
        self._seen_keys: set[str] = set()

    def check(self, message: TelegramMessageEnvelope) -> DeduplicationDecision:
        dedup_key = message.dedup_key or build_input_dedup_key(message)
        is_duplicate = dedup_key in self._seen_keys
        if not is_duplicate:
            self._seen_keys.add(dedup_key)

        return DeduplicationDecision(
            scope=DeduplicationScope.MULTIMODAL_INPUT,
            is_duplicate=is_duplicate,
            dedup_key=dedup_key,
            matched_key=dedup_key if is_duplicate else None,
            reasons=["duplicate multimodal Telegram input"] if is_duplicate else [],
        )
