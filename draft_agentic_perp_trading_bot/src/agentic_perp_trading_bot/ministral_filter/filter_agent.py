"""Draft Ministral3-8B/14B filter interface."""

from __future__ import annotations

from agentic_perp_trading_bot.ministral_filter.signal_deduplication import (
    InMemorySignalDeduplicator,
)
from agentic_perp_trading_bot.schemas import FilterDecision, QwenSignalHypothesis


class MinistralFilterAgent:
    def __init__(
        self,
        model_id: str,
        signal_deduplicator: InMemorySignalDeduplicator | None = None,
    ):
        self.model_id = model_id
        self.signal_deduplicator = signal_deduplicator

    async def review(self, hypothesis: QwenSignalHypothesis) -> FilterDecision:
        """Validate, deduplicate, quality-score, and canonicalize a QWEN hypothesis."""
        deduplication = None
        if self.signal_deduplicator is not None:
            deduplication = self.signal_deduplicator.check(hypothesis)
            if deduplication.is_duplicate:
                return FilterDecision(
                    status="rejected",
                    quality_score=0.0,
                    canonical_intent=None,
                    rejection_reasons=deduplication.reasons,
                    reviewer_model=self.model_id,
                    deduplication=deduplication,
                )

        return FilterDecision(
            status="rejected",
            quality_score=0.0,
            canonical_intent=None,
            rejection_reasons=["placeholder implementation"],
            reviewer_model=self.model_id,
            deduplication=deduplication,
        )
