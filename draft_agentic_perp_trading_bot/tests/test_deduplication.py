from decimal import Decimal

from agentic_perp_trading_bot.ministral_filter.signal_deduplication import (
    InMemorySignalDeduplicator,
)
from agentic_perp_trading_bot.schemas import IntentType, QwenSignalHypothesis, StrategyTier
from agentic_perp_trading_bot.telegram_ingestion.deduplication import (
    InMemoryTelegramDeduplicator,
)
from agentic_perp_trading_bot.telegram_ingestion.normalizer import normalize_telegram_update


def test_telegram_normalizer_builds_stable_input_dedup_key() -> None:
    update = {
        "channel_id": "owner_a_channel_a",
        "message_id": 123,
        "text": "ETH 多",
        "media_hashes": ["chart-hash"],
    }

    first = normalize_telegram_update(update)
    second = normalize_telegram_update(update)

    assert first.dedup_key == second.dedup_key
    assert first.content_hash == second.content_hash


def test_telegram_deduplicator_flags_second_input() -> None:
    message = normalize_telegram_update(
        {
            "channel_id": "owner_a_channel_a",
            "message_id": 123,
            "text": "ETH 多",
        }
    )
    deduplicator = InMemoryTelegramDeduplicator()

    assert not deduplicator.check(message).is_duplicate
    assert deduplicator.check(message).is_duplicate


def test_signal_deduplicator_flags_second_trading_hypothesis() -> None:
    message = normalize_telegram_update(
        {
            "channel_id": "owner_a_channel_a",
            "message_id": 123,
            "text": "ETH 多 3500",
        }
    )
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
