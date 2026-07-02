"""Draft Ministral3-8B/14B filter interface."""

from __future__ import annotations

from agentic_perp_trading_bot.schemas import FilterDecision, QwenSignalHypothesis


class MinistralFilterAgent:
    def __init__(self, model_id: str):
        self.model_id = model_id

    async def review(self, hypothesis: QwenSignalHypothesis) -> FilterDecision:
        """Validate, quality-score, and optionally canonicalize a QWEN hypothesis."""
        return FilterDecision(
            status="rejected",
            quality_score=0.0,
            canonical_intent=None,
            rejection_reasons=["placeholder implementation"],
            reviewer_model=self.model_id,
        )
