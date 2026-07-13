"""Normalize raw Telegram updates into owner/channel-aware message envelopes."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from agentic_perp_trading_bot.schemas import AssetGroup, OwnerId, TelegramMessageEnvelope
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


def _media_hashes(update: dict[str, Any]) -> list[str]:
    explicit_hashes = update.get("media_hashes")
    if explicit_hashes:
        return sorted(str(item) for item in explicit_hashes)

    media_s3_uri = update.get("media_s3_uri")
    if media_s3_uri is None:
        return []
    return [_sha256_text(str(media_s3_uri))]


def normalize_telegram_update(update: dict[str, Any]) -> TelegramMessageEnvelope:
    """Convert a raw Telegram update into the canonical ingestion envelope."""
    channel_id = str(update["channel_id"])
    owner_id, asset_group = OWNER_CHANNEL_MAP[channel_id]
    raw_text = update.get("text")
    content_hash = _sha256_text(raw_text.strip()) if isinstance(raw_text, str) else None

    envelope = TelegramMessageEnvelope(
        owner_id=owner_id,
        channel_id=channel_id,
        asset_group=asset_group,
        telegram_message_id=str(update["message_id"]),
        received_at=datetime.now(timezone.utc),
        raw_text=raw_text,
        media_s3_uri=update.get("media_s3_uri"),
        content_hash=content_hash,
        media_hashes=_media_hashes(update),
    )
    envelope.dedup_key = build_input_dedup_key(envelope)
    return envelope
