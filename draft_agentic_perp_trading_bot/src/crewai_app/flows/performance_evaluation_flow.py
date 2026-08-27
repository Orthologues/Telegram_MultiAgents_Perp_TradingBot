"""CrewAI Flow for matched-venue and five-tier strategy evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

from crewai.flow.flow import Flow, listen, start

from crewai_app.domain.contracts.schemas import (
    StrategyTier,
    TestnetVenuePerformanceComparison,
)
from crewai_app.domain.performance.metrics import summarize_strategy_tiers
from crewai_app.domain.performance.venue_comparison import (
    compare_testnet_venue_performance,
)
from crewai_app.flows.states import (
    PerformanceEvaluationState,
    StrategyTierPerformanceSummary,
)


class PerformanceEvaluationFlow(Flow[PerformanceEvaluationState]):
    """Evaluate venue reliability and every strategy tier separately."""

    initial_state = PerformanceEvaluationState

    def __init__(self, *, tracing: bool = False) -> None:
        super().__init__(suppress_flow_events=True, tracing=tracing)

    @start()
    def compare_matched_testnet_venues(self) -> TestnetVenuePerformanceComparison:
        computed_at = self.state.computed_at or datetime.now(timezone.utc)
        self.state.computed_at = computed_at
        self.state.venue_comparison = compare_testnet_venue_performance(
            self.state.closed_outcomes,
            computed_at=computed_at,
        )
        return self.state.venue_comparison

    @listen(compare_matched_testnet_venues)
    def evaluate_five_strategy_tiers(
        self,
    ) -> dict[StrategyTier, StrategyTierPerformanceSummary]:
        self.state.strategy_summaries = summarize_strategy_tiers(
            self.state.strategy_outcomes
        )
        return self.state.strategy_summaries
