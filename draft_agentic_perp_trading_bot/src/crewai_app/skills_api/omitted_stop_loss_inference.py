"""Typed API for the omitted stop-loss inference skill.

File mappings:
``skills_api/omitted_stop_loss_inference.py`` <-
``frameworkless_app/skills_api/omitted_stop_loss_inference.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

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
