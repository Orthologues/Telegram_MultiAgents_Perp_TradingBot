"""Typed API for the omitted stop-loss inference skill."""

from __future__ import annotations

from typing import Protocol

from crewai_app.domain.contracts.schemas import (
    MarketAnalysisSnapshot,
    OmittedStopLossDecision,
    QwenSignalHypothesis,
)


class OmittedStopLossInferenceAPI(Protocol):
    def infer_omitted_stop_loss(
        self,
        hypothesis: QwenSignalHypothesis,
        market_snapshot: MarketAnalysisSnapshot | None,
    ) -> OmittedStopLossDecision | None: ...
