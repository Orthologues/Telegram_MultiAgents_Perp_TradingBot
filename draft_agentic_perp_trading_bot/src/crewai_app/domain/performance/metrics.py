"""Five-tier performance metrics and canonical sizing export.

File mappings:
``domain/performance/position_sizing.py`` <-
``frameworkless_app/performance_engine/weight_engine.py``;
``domain/contracts/schemas.py`` <- ``frameworkless_app/schemas.py``.
"""

from decimal import Decimal
from typing import List, Set

from crewai_app.domain.contracts.schemas import (
    AssetGroup,
    OwnerId,
    StrategyOutcome,
    StrategyTier,
    StrategyTierPerformanceSummary,
)
from crewai_app.domain.performance.position_sizing import compute_position_size


def summarize_strategy_tiers(
    outcomes: List[StrategyOutcome],
) -> dict[StrategyTier, StrategyTierPerformanceSummary]:
    """Return a summary for every tier, including counterfactual replays."""
    unique_outcomes = _closed_unique_outcomes(outcomes)
    summaries: dict[StrategyTier, StrategyTierPerformanceSummary] = {}
    for tier in StrategyTier:
        summaries[tier] = _build_summary(
            tier,
            [item for item in unique_outcomes if item.strategy_tier == tier],
        )
    return summaries


def summarize_strategy_dimensions(
    outcomes: List[StrategyOutcome],
) -> List[StrategyTierPerformanceSummary]:
    """Summarize each tier by owner, channel, asset group, and lifecycle stage."""
    grouped: dict[
        tuple[OwnerId | None, str | None, AssetGroup | None, str | None, StrategyTier],
        List[StrategyOutcome],
    ] = {}
    for item in _closed_unique_outcomes(outcomes):
        outcome = item.outcome
        key = (
            outcome.owner_id,
            outcome.channel_id,
            outcome.asset_group,
            outcome.lifecycle_stage,
            item.strategy_tier,
        )
        grouped.setdefault(key, []).append(item)

    def sort_key(
        key: tuple[OwnerId | None, str | None, AssetGroup | None, str | None, StrategyTier],
    ) -> tuple[str, str, str, str, str]:
        return tuple(
            value.value if isinstance(value, (OwnerId, AssetGroup, StrategyTier)) else value or ""
            for value in key
        )

    return [
        _build_summary(
            tier,
            items,
            owner_id=owner_id,
            channel_id=channel_id,
            asset_group=asset_group,
            lifecycle_stage=lifecycle_stage,
        )
        for (
            owner_id,
            channel_id,
            asset_group,
            lifecycle_stage,
            tier,
        ), items in sorted(grouped.items(), key=lambda item: sort_key(item[0]))
    ]


def _closed_unique_outcomes(
    outcomes: List[StrategyOutcome],
) -> List[StrategyOutcome]:
    seen: Set[tuple[StrategyTier, str]] = set()
    unique: List[StrategyOutcome] = []
    for item in outcomes:
        if not item.outcome.fully_closed:
            continue
        identity = (
            item.strategy_tier,
            item.outcome.outcome_id or item.outcome.model_dump_json(),
        )
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(item)
    return unique


def _build_summary(
    tier: StrategyTier,
    matching: List[StrategyOutcome],
    *,
    owner_id: OwnerId | None = None,
    channel_id: str | None = None,
    asset_group: AssetGroup | None = None,
    lifecycle_stage: str | None = None,
) -> StrategyTierPerformanceSummary:
    executed = [item for item in matching if not item.counterfactual]
    counterfactual = [item for item in matching if item.counterfactual]
    percentages = [item.outcome.net_pnl_percentage for item in matching]
    return StrategyTierPerformanceSummary(
        strategy_tier=tier,
        owner_id=owner_id,
        channel_id=channel_id,
        asset_group=asset_group,
        lifecycle_stage=lifecycle_stage,
        sample_count=len(matching),
        executed_count=len(executed),
        counterfactual_count=len(counterfactual),
        profitable_count=sum(value > 0 for value in percentages),
        losing_count=sum(value < 0 for value in percentages),
        net_pnl_percentage=sum(percentages, start=Decimal("0")),
        executed_net_pnl_percentage=sum(
            (item.outcome.net_pnl_percentage for item in executed),
            start=Decimal("0"),
        ),
        counterfactual_net_pnl_percentage=sum(
            (item.outcome.net_pnl_percentage for item in counterfactual),
            start=Decimal("0"),
        ),
    )


__all__ = [
    "compute_position_size",
    "summarize_strategy_dimensions",
    "summarize_strategy_tiers",
]
