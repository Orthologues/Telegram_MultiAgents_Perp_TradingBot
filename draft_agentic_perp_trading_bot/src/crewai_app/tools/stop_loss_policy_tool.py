"""Flow-only deterministic omitted stop-loss tool."""

from pydantic import BaseModel

from crewai_app.domain.contracts.schemas import (
    MarketAnalysisSnapshot,
    QwenSignalHypothesis,
)
from crewai_app.domain.policies.stop_loss import MinistralStopLossPolicy
from crewai_app.tools._base import TradingBotTool


class StopLossPolicyInput(BaseModel):
    hypothesis: QwenSignalHypothesis
    market_snapshot: MarketAnalysisSnapshot


class StopLossPolicyTool(TradingBotTool):
    name: str = "infer_omitted_stop_loss"
    description: str = "Apply deterministic omitted stop-loss policy outside the agents."
    args_schema: type[BaseModel] = StopLossPolicyInput
    agent_accessible: bool = False

    def _run(
        self,
        hypothesis: QwenSignalHypothesis | dict,
        market_snapshot: MarketAnalysisSnapshot | dict,
    ) -> dict | None:
        decision = MinistralStopLossPolicy().derive(
            QwenSignalHypothesis.model_validate(hypothesis),
            MarketAnalysisSnapshot.model_validate(market_snapshot),
        )
        return decision.model_dump(mode="json") if decision is not None else None
