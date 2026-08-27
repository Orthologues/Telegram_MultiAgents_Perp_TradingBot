"""Flow-only deterministic confidence-policy tool."""

from pydantic import BaseModel, Field

from crewai_app.domain.contracts.schemas import PerformanceMetricsSnapshot
from crewai_app.domain.policies.confidence import evaluate_confidence
from crewai_app.tools._base import TradingBotTool


class ConfidencePolicyInput(BaseModel):
    source_confidence: float = Field(ge=0.0, le=1.0)
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    performance: PerformanceMetricsSnapshot | None = None


class ConfidencePolicyTool(TradingBotTool):
    name: str = "apply_confidence_policy"
    description: str = "Apply deterministic confidence selection outside agent reasoning."
    args_schema: type[BaseModel] = ConfidencePolicyInput
    agent_accessible: bool = False

    def _run(
        self,
        source_confidence: float,
        quality_score: float | None = None,
        performance: PerformanceMetricsSnapshot | dict | None = None,
    ) -> dict:
        snapshot = (
            PerformanceMetricsSnapshot.model_validate(performance)
            if performance is not None
            else None
        )
        return evaluate_confidence(
            source_confidence,
            quality_score=quality_score,
            performance=snapshot,
        ).model_dump(mode="json")
