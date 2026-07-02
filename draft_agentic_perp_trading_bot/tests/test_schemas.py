from datetime import datetime, timezone

from agentic_perp_trading_bot.schemas import AssetGroup, OwnerId, TelegramMessageEnvelope


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
