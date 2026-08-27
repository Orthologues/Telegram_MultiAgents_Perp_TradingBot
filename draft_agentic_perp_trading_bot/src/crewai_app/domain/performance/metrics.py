"""Compatibility-backed sizing and five-tier performance metrics."""

from decimal import Decimal

from agentic_perp_trading_bot.performance_engine.weight_engine import compute_position_size
from crewai_app.domain.contracts.schemas import StrategyTier
from crewai_app.flows.states import StrategyOutcome, StrategyTierPerformanceSummary


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
