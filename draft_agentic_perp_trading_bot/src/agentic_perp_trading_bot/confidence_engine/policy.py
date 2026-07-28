"""Replayable confidence scoring and five-tier strategy selection."""

from __future__ import annotations

from agentic_perp_trading_bot.schemas import (
    ConfidenceDecision,
    PerformanceMetricsSnapshot,
    StrategyTier,
)

CONFIDENCE_FORMULA_VERSION = "synthetic-v2"


def evaluate_confidence(
    source_confidence: float,
    *,
    quality_score: float | None = None,
    performance: PerformanceMetricsSnapshot | None = None,
) -> ConfidenceDecision:
    """Combine source, Ministral quality, and replay metrics without hard gating."""
    source_score = _unit_interval(source_confidence)
    quality = _unit_interval(quality_score) if quality_score is not None else None
    performance_score = _performance_score(performance) if performance is not None else None

    weighted_components = [(source_score, 0.45)]
    if quality is not None:
        weighted_components.append((quality, 0.25))
    if performance_score is not None:
        weighted_components.append((performance_score, 0.30))
    total_weight = sum(weight for _, weight in weighted_components)
    confidence = sum(score * weight for score, weight in weighted_components) / total_weight

    reasons: list[str] = []
    if quality is None:
        reasons.append("ministral_quality_score_unavailable")
    if performance_score is None:
        reasons.append("execution_performance_history_unavailable")

    return ConfidenceDecision(
        confidence=confidence,
        strategy_tier=_strategy_tier_for(confidence),
        source_confidence=source_score,
        quality_score=quality,
        performance_score=performance_score,
        formula_version=CONFIDENCE_FORMULA_VERSION,
        reasons=reasons,
    )


def _performance_score(snapshot: PerformanceMetricsSnapshot) -> float:
    pnl_score = _unit_interval(
        0.5 + float(snapshot.cumulative_pnl_percentage) / 200.0
    )
    return _unit_interval(
        snapshot.tp1_hit_rate * 0.20
        + snapshot.tp2_hit_rate * 0.25
        + (1.0 - snapshot.stop_loss_rate) * 0.20
        + pnl_score * 0.20
        + (1.0 - snapshot.immediate_reversal_after_stop_rate) * 0.15
    )


def _unit_interval(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


def _strategy_tier_for(confidence: float) -> StrategyTier:
    if confidence < 0.2:
        return StrategyTier.ULTRA_CONSERVATIVE
    if confidence < 0.4:
        return StrategyTier.CONSERVATIVE
    if confidence < 0.6:
        return StrategyTier.INTERMEDIATE
    if confidence < 0.8:
        return StrategyTier.RADICAL
    return StrategyTier.ULTRA_RADICAL
