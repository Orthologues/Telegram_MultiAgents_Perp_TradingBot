"""Normalize AG2 TelegramAgent retrievals into owner-aware envelopes."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from agentic_perp_trading_bot.schemas import (
    AssetGroup,
    OwnerId,
    TelegramAgentRetrievedMessage,
    TelegramMessageEnvelope,
)
from agentic_perp_trading_bot.telegram_ingestion.deduplication import build_input_dedup_key


OWNER_CHANNEL_MAP: dict[str, tuple[OwnerId, AssetGroup]] = {
    "owner_a_channel_a": (OwnerId.OWNER_A_SHU_QIN, AssetGroup.MIXED),
    "owner_b_channel_a": (OwnerId.OWNER_B_LAO_TU, AssetGroup.MIXED),
    "owner_c_btc_eth": (OwnerId.OWNER_C_BI_JIA_SUO, AssetGroup.BTC_ETH),
    "owner_c_alts_tradfi": (OwnerId.OWNER_C_BI_JIA_SUO, AssetGroup.ALTS),
    "owner_d_btc_eth": (OwnerId.OWNER_D_A_ZHU, AssetGroup.BTC_ETH),
    "owner_d_alts_day": (OwnerId.OWNER_D_A_ZHU, AssetGroup.ALTS),
    "owner_d_alts_longer": (OwnerId.OWNER_D_A_ZHU, AssetGroup.ALTS),
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_telegram_agent_message(
    message: TelegramAgentRetrievedMessage | dict[str, Any],
    *,
    channel_id: str,
    telegram_chat_id: str,
    observed_at: datetime | None = None,
    media_s3_uri: str | None = None,
    media_hashes: Iterable[str] = (),
) -> TelegramMessageEnvelope:
    """Convert one AG2 retrieval result into the canonical ingestion envelope."""
    retrieved = TelegramAgentRetrievedMessage.model_validate(message)
    owner_id, asset_group = OWNER_CHANNEL_MAP[channel_id]
    normalized_media_hashes = sorted(str(item) for item in media_hashes)

    envelope = TelegramMessageEnvelope(
        owner_id=owner_id,
        channel_id=channel_id,
        asset_group=asset_group,
        telegram_chat_id=telegram_chat_id,
        telegram_message_id=retrieved.id,
        source_timestamp=retrieved.date,
        received_at=observed_at or datetime.now(timezone.utc),
        sender_id=retrieved.from_id,
        reply_to_message_id=retrieved.reply_to_msg_id,
        parent_messages=[retrieved.reply_to_msg_id] if retrieved.reply_to_msg_id else [],
        forwarded_from_id=retrieved.forward_from,
        edited_at=retrieved.edit_date,
        raw_text=retrieved.text,
        raw_media_present=retrieved.media,
        media_s3_uri=media_s3_uri,
        content_hash=_sha256_text(retrieved.text) if retrieved.text is not None else None,
        media_hashes=normalized_media_hashes,
    )
    envelope.dedup_key = build_input_dedup_key(envelope)
    return envelope


def attach_archived_media(
    message: TelegramMessageEnvelope,
    *,
    media_s3_uri: str,
    media_hashes: Iterable[str],
) -> TelegramMessageEnvelope:
    """Attach durable media identity and replace the provisional dedup key."""
    normalized_media_hashes = sorted(str(item) for item in media_hashes)
    if not normalized_media_hashes:
        raise ValueError("at least one media hash is required for archived Telegram media")

    enriched = message.model_copy(
        update={
            "media_s3_uri": media_s3_uri,
            "media_hashes": normalized_media_hashes,
        }
    )
    enriched.dedup_key = build_input_dedup_key(enriched)
    return enriched
