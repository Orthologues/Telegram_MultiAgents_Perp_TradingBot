from decimal import Decimal

from frameworkless_app.ministral_filter.signal_deduplication import (
    InMemorySignalDeduplicator,
)
from frameworkless_app.schemas import IntentType, QwenSignalHypothesis, StrategyTier
from frameworkless_app.telegram_ingestion.deduplication import (
    InMemoryTelegramDeduplicator,
)
from frameworkless_app.telegram_ingestion.normalizer import (
    normalize_telegram_agent_message,
)


def _normalize(message_id: str, text: str, *, media_hashes: list[str] | None = None):
    return normalize_telegram_agent_message(
        {
            "id": message_id,
            "date": "2026-07-20T09:30:00+00:00",
            "text": text,
            "media": bool(media_hashes),
        },
        channel_id="owner_a_channel_a",
        telegram_chat_id="-1001234567890",
        media_hashes=media_hashes or [],
    )


def test_telegram_normalizer_builds_stable_input_dedup_key() -> None:
    first = _normalize("123", "ETH 多", media_hashes=["chart-hash"])
    second = _normalize("123", "ETH 多", media_hashes=["chart-hash"])

    assert first.dedup_key == second.dedup_key
    assert first.content_hash == second.content_hash


def test_telegram_deduplicator_flags_second_input() -> None:
    message = _normalize("123", "ETH 多")
    deduplicator = InMemoryTelegramDeduplicator()

    assert not deduplicator.check(message).is_duplicate
    assert deduplicator.check(message).is_duplicate


def test_signal_deduplicator_flags_second_trading_hypothesis() -> None:
    message = _normalize("123", "ETH 多 3500")
    signal = QwenSignalHypothesis(
        owner_id=message.owner_id,
        channel_id=message.channel_id,
        asset_group=message.asset_group,
        strategy_tier=StrategyTier.INTERMEDIATE,
        intent_type=IntentType.NEW_ORDER,
        symbol="ETHUSDT",
        direction="long",
        entries=[Decimal("3500")],
        stop_loss=Decimal("3400"),
        take_profit=[Decimal("3600")],
        confidence=0.8,
    )
    deduplicator = InMemorySignalDeduplicator()

    assert not deduplicator.check(signal).is_duplicate
    assert deduplicator.check(signal).is_duplicate
