"""Draft trading-signal deduplication before sizing and execution."""

from __future__ import annotations

import hashlib
from decimal import Decimal

from agentic_perp_trading_bot.schemas import (
    DeduplicationDecision,
    DeduplicationScope,
    QwenSignalHypothesis,
)


def _decimal_list_key(values: list[Decimal]) -> str:
    return ",".join(str(value.normalize()) for value in sorted(values))


def build_signal_dedup_key(hypothesis: QwenSignalHypothesis) -> str:
    payload = "|".join(
        [
            str(hypothesis.owner_id),
            hypothesis.channel_id,
            str(hypothesis.asset_group),
            str(hypothesis.strategy_tier),
            str(hypothesis.intent_type),
            hypothesis.symbol.upper() if hypothesis.symbol else "no_symbol",
            hypothesis.direction.lower() if hypothesis.direction else "no_direction",
            _decimal_list_key(hypothesis.entries),
            str(hypothesis.stop_loss.normalize()) if hypothesis.stop_loss is not None else "no_sl",
            _decimal_list_key(hypothesis.take_profit),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class InMemorySignalDeduplicator:
    """Process-local placeholder for duplicate QWEN trading hypotheses."""

    def __init__(self) -> None:
        self._seen_keys: set[str] = set()

    def check(self, hypothesis: QwenSignalHypothesis) -> DeduplicationDecision:
        dedup_key = build_signal_dedup_key(hypothesis)
        is_duplicate = dedup_key in self._seen_keys
        if not is_duplicate:
            self._seen_keys.add(dedup_key)

        return DeduplicationDecision(
            scope=DeduplicationScope.TRADING_SIGNAL,
            is_duplicate=is_duplicate,
            dedup_key=dedup_key,
            matched_key=dedup_key if is_duplicate else None,
            reasons=["duplicate trading signal"] if is_duplicate else [],
        )
