"""Five-tier performance metrics and canonical sizing export.

File mappings:
``domain/performance/position_sizing.py`` <-
``frameworkless_app/performance_engine/weight_engine.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from decimal import Decimal

from crewai_app.domain.contracts.schemas import StrategyTier
from crewai_app.flows.states import StrategyOutcome, StrategyTierPerformanceSummary
from crewai_app.domain.performance.position_sizing import compute_position_size


def summarize_strategy_tiers(
    outcomes: list[StrategyOutcome],
) -> dict[StrategyTier, StrategyTierPerformanceSummary]:
    """Return a summary for every tier, including counterfactual replays."""
    summaries: dict[StrategyTier, StrategyTierPerformanceSummary] = {}
    for tier in StrategyTier:
        matching = [item for item in outcomes if item.strategy_tier == tier]
        percentages = [item.outcome.net_pnl_percentage for item in matching]
        summaries[tier] = StrategyTierPerformanceSummary(
            strategy_tier=tier,
            sample_count=len(matching),
            executed_count=sum(not item.counterfactual for item in matching),
            counterfactual_count=sum(item.counterfactual for item in matching),
            profitable_count=sum(value > 0 for value in percentages),
            losing_count=sum(value < 0 for value in percentages),
            net_pnl_percentage=sum(percentages, start=Decimal("0")),
        )
    return summaries


__all__ = ["compute_position_size", "summarize_strategy_tiers"]
