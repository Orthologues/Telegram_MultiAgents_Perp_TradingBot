"""Draft multimodal Telegram input deduplication.

The production implementation should persist keys in DynamoDB, Redis, or another
shared store so Lambda/ECS workers deduplicate across processes.
"""

from __future__ import annotations

from agentic_perp_trading_bot.schemas import (
    DeduplicationDecision,
    DeduplicationScope,
    TelegramMessageEnvelope,
)


def build_input_dedup_key(message: TelegramMessageEnvelope) -> str:
    text_hash = message.content_hash or "no_text"
    media_hashes = ",".join(sorted(message.media_hashes)) or "no_media"
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
