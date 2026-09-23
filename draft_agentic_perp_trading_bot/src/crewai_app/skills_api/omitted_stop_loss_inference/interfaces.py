"""Compatibility API for the deterministic omitted-stop-loss policy.

The canonical implementation is domain.policies.stop_loss exposed to a Flow
through tools.stop_loss_policy_tool; this module is not a model interface.

File mappings:
``skills_api/omitted_stop_loss_inference/interfaces.py`` <-
``frameworkless_app/skills_api/omitted_stop_loss_inference.py``;
``domain/contracts/__init__.py`` <- ``frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from typing import Protocol

from crewai_app.domain.contracts import (
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
