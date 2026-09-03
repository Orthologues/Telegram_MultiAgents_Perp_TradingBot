import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from frameworkless_app.schemas import (
    AssetGroup,
    OwnerId,
    OwnerRagProfile,
    SerialRagExample,
    StrategyTier,
    TelegramMessageEnvelope,
    TelegramRagMessageReference,
)


def test_telegram_message_envelope_constructs() -> None:
    envelope = TelegramMessageEnvelope(
        owner_id=OwnerId.OWNER_A_SHU_QIN,
        channel_id="owner_a_channel_a",
        asset_group=AssetGroup.MIXED,
        telegram_message_id="123",
        received_at=datetime.now(timezone.utc),
        raw_text="ETH 多",
    )

    assert envelope.owner_id == OwnerId.OWNER_A_SHU_QIN
    assert envelope.language_hint == "zh"


def test_owner_rag_profiles_reserve_private_s3_archive_and_examples() -> None:
    profile_root = Path(__file__).parents[1] / "rag_profiles"

    for profile_path in sorted(profile_root.glob("*/shared_style.json")):
        profile = OwnerRagProfile.model_validate(
            json.loads(profile_path.read_text(encoding="utf-8"))
        )
        assert profile.s3_archive_prefix.startswith("s3://")
        assert profile.serial_rag_examples == []


def test_serial_rag_example_requires_ordered_telegram_provenance_and_s3() -> None:
    example = SerialRagExample(
        example_id="owner-a-btc-001",
        strategy_tier=StrategyTier.INTERMEDIATE,
        messages=[
            TelegramRagMessageReference(
                telegram_message_id="100",
                telegram_message_url="https://t.me/c/123/100",
            ),
            TelegramRagMessageReference(
                telegram_message_id="101",
                telegram_message_url="https://t.me/c/123/101",
            ),
        ],
        s3_archive_uri="s3://private-rag-bucket/owner-a-btc-001.json",
        execution_label="ambiguous",
    )

    assert [message.telegram_message_id for message in example.messages] == [
        "100",
        "101",
    ]

    with pytest.raises(ValueError, match="chronological"):
        SerialRagExample(
            example_id="owner-a-btc-002",
            strategy_tier=StrategyTier.INTERMEDIATE,
            messages=list(reversed(example.messages)),
            s3_archive_uri="s3://private-rag-bucket/owner-a-btc-002.json",
            execution_label="ambiguous",
        )
