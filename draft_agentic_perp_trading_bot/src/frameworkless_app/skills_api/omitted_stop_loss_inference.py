"""Typed API for the Omitted Stop-Loss Inference skill."""

from __future__ import annotations

from typing import Protocol

from frameworkless_app.schemas import (
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
