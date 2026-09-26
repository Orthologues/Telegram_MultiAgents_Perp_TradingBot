"""Deterministic orchestration service used by the CrewAI Telegram Flow.

File mappings:
``flows/orchestration.py`` <- ``frameworkless_app/orchestrator.py``;
``domain/policies/confidence.py`` <- ``frameworkless_app/confidence_engine/policy.py``;
``domain/performance/position_sizing.py`` <-
``frameworkless_app/performance_engine/weight_engine.py``;
``adapters/telegram/deduplication.py`` <-
``frameworkless_app/telegram_ingestion/deduplication.py``;
``domain/lifecycle/cursor.py`` <- ``frameworkless_app/trade_cursor.py``;
``domain/contracts/__init__.py`` <- ``frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from crewai_app.agent_interfaces.ministral import MinistralReviewAPI
from crewai_app.agent_interfaces.qwen import (
    LegacySignalInferenceAPI,
    QwenCandidateInferenceAPI,
)
from crewai_app.domain.policies.confidence import evaluate_confidence
from crewai_app.domain.performance.position_sizing import compute_position_size
from crewai_app.domain.policies.execution_gate import (
    evaluate_deterministic_risk,
    validate_market_snapshot,
)
from crewai_app.domain.policies.funding_rate import (
    evaluate_funding_rate_cycle_filter,
)
from crewai_app.domain.policies.stop_loss import MinistralStopLossPolicy
from crewai_app.domain.contracts import (
    ApprovedExecutionRequest,
    CanonicalTradeIntent,
    ConfidenceDecision,
    ExchangeId,
    ExchangeNetwork,
    FilterDecision,
    IntentType,
    LifecycleStrategySource,
    MarketAnalysisSnapshot,
    MarketExecutionSnapshot,
    PairRiskLimit,
    PerformanceMetricsSnapshot,
    PositionDirection,
    PositionLifecycleStrategy,
    PositionSizingDecision,
    QwenSignalHypothesis,
    QwenStrategyCandidateSet,
    StrategyTier,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradeAction,
    TradeThreadCursor,
)
from crewai_app.adapters.telegram.deduplication import InMemoryTelegramDeduplicator
from crewai_app.domain.lifecycle.cursor import ConcurrentTradeCursorManager

__all__ = ["process_message"]


async def process_message(
    message: TelegramMessageEnvelope,
    qwen_agent: QwenCandidateInferenceAPI | LegacySignalInferenceAPI,
    filter_agent: MinistralReviewAPI,
    telegram_deduplicator: InMemoryTelegramDeduplicator | None = None,
    prompt_context: TelegramPromptContext | None = None,
    pair_blacklisted: bool = False,
    current_price: Decimal | None = None,
    reference_price: Decimal | None = None,
    market_snapshot: MarketAnalysisSnapshot | None = None,
    tradfi_perpetual_pair: bool = False,
    trade_cursor_manager: ConcurrentTradeCursorManager | None = None,
    performance_snapshot: PerformanceMetricsSnapshot | None = None,
    risk_limits: Mapping[ExchangeId, PairRiskLimit] | None = None,
    existing_position_notional_by_exchange: Mapping[ExchangeId, Decimal] | None = None,
    market_snapshots: Mapping[ExchangeId, MarketExecutionSnapshot] | None = None,
    selected_strategy_tier: StrategyTier | None = None,
) -> ApprovedExecutionRequest | None:
    """Run one normalized message through review, selection, and deterministic policy."""
    if telegram_deduplicator is not None:
        input_deduplication = telegram_deduplicator.inspect(message)
        if input_deduplication.is_duplicate:
            return None

    context = prompt_context or TelegramPromptContext.from_message(message)
    if trade_cursor_manager is not None and not context.active_trade_cursors:
        active_trade_cursors = await trade_cursor_manager.resolve_for_message(message)
        context = context.model_copy(
            update={"active_trade_cursors": active_trade_cursors}
        )
    hypotheses, source_confidence, complete_candidate_set = await _infer_hypotheses(
        qwen_agent,
        message,
        context,
    )
    filter_decisions: dict[
        StrategyTier,
        tuple[QwenSignalHypothesis, FilterDecision],
    ] = {}
    for hypothesis in hypotheses:
        hypothesis.source_dedup_key = message.dedup_key
        decision = await filter_agent.review(hypothesis, context, market_snapshot)
        if decision.status == "approved" and decision.canonical_intent is not None:
            filter_decisions[hypothesis.strategy_tier] = (hypothesis, decision)

    if not filter_decisions:
        return None

    lifecycle_cursors = _matching_lifecycle_cursors(
        filter_decisions,
        context.active_trade_cursors,
    )
    inherited_strategy = _shared_lifecycle_strategy(lifecycle_cursors)
    transition_requested = (
        inherited_strategy is not None
        and message.strategy_tier_hint is not None
        and message.strategy_tier_hint != inherited_strategy.strategy_tier
    )

    selected_tier = _resolve_strategy_tier(
        message,
        selected_strategy_tier,
        filter_decisions,
        lifecycle_cursors,
    )
    if selected_tier is None:
        if complete_candidate_set or transition_requested:
            return None
        selected_tier, selected = next(iter(filter_decisions.items()))
    else:
        selected = filter_decisions[selected_tier]

    confidence = _score_confidence(
        message,
        source_confidence,
        selected_tier,
        filter_decisions,
        lifecycle_cursors,
        performance_snapshot,
    )

    hypothesis, filter_decision = selected
    canonical_intent = filter_decision.canonical_intent
    assert canonical_intent is not None
    if inherited_strategy is not None and not any(
        _cursor_matches_intent(cursor, canonical_intent)
        for cursor in lifecycle_cursors
    ):
        return None
    if canonical_intent.stop_loss is None:
        omitted_stop_loss = filter_decision.omitted_stop_loss
        if omitted_stop_loss is None:
            policy_market_snapshot = _market_snapshot_for_stop_loss(
                hypothesis,
                market_snapshot,
                market_snapshots,
            )
            if policy_market_snapshot is not None:
                omitted_stop_loss = MinistralStopLossPolicy().derive(
                    hypothesis,
                    policy_market_snapshot,
                )
        if omitted_stop_loss is not None:
            canonical_intent = canonical_intent.model_copy(
                update={"stop_loss": omitted_stop_loss.stop_loss}
            )

    effective_current_price = current_price
    if effective_current_price is None and market_snapshot is not None:
        effective_current_price = market_snapshot.current_price

    intent = canonical_intent.model_copy(
        update={"strategy_tier": confidence.strategy_tier}
    )
    if inherited_strategy is not None and not transition_requested:
        sizing = _sizing_from_lifecycle(intent, inherited_strategy)
        lifecycle_strategy = inherited_strategy
    else:
        sizing = compute_position_size(
            filter_decision.model_copy(update={"canonical_intent": intent})
        )
        lifecycle_strategy = _new_lifecycle_strategy(
            message,
            confidence,
            sizing,
            previous=inherited_strategy,
        )
    limits_by_exchange = risk_limits or {}
    current_notional_by_exchange = existing_position_notional_by_exchange or {}
    expected_reference_price = (
        reference_price
        if reference_price is not None
        else (hypothesis.entries[0] if hypothesis.entries else None)
    )
    if market_snapshots is not None:
        target_exchanges = set(intent.target_exchanges)
        if expected_reference_price is None:
            return None
        if target_exchanges - set(market_snapshots):
            return None
        if any(
            _snapshot_rejection_reasons(
                market_snapshots[exchange_id],
                exchange_id=exchange_id,
                network=intent.execution_network,
                symbol=intent.symbol,
                reference_price=expected_reference_price,
                intent_type=hypothesis.intent_type,
            )
            for exchange_id in intent.target_exchanges
        ):
            return None
    risk_decisions = [
        evaluate_deterministic_risk(
            sizing,
            exchange_id=exchange_id,
            network=intent.execution_network,
            symbol=intent.symbol,
            limits=limits_by_exchange.get(exchange_id)
            or _default_risk_limit(
                message,
                exchange_id,
                intent.execution_network,
                intent.symbol,
            ),
            existing_position_notional_usd=current_notional_by_exchange.get(
                exchange_id,
                Decimal("0"),
            ),
            pair_blacklisted=pair_blacklisted,
            instant_order=intent.order_type == "market",
            current_price=(
                market_snapshots[exchange_id].market.current_price
                if market_snapshots is not None
                else effective_current_price
            ),
            reference_price=(
                market_snapshots[exchange_id].reference_price
                if market_snapshots is not None
                else reference_price
            ),
            asset_group=intent.asset_group,
            tradfi_perpetual_pair=tradfi_perpetual_pair,
        )
        for exchange_id in dict.fromkeys(intent.target_exchanges)
    ]
    if not risk_decisions or any(not decision.approved for decision in risk_decisions):
        return None

    if hypothesis.intent_type != IntentType.NEW_ORDER:
        matched_exchanges = {
            cursor.exchange_id
            for cursor in lifecycle_cursors
            if _cursor_matches_intent(cursor, intent)
        }
        if matched_exchanges != set(intent.target_exchanges):
            return None

    request = ApprovedExecutionRequest(
        intent=intent,
        sizing=sizing,
        confidence=confidence,
        lifecycle_strategy=lifecycle_strategy,
        risk_decisions=risk_decisions,
        idempotency_key=message.dedup_key
        or f"{message.channel_id}:{message.telegram_message_id}",
        source_telegram_message_id=message.telegram_message_id,
        parent_message_ids=list(message.parent_messages),
    )
    trade_cursors = []
    if trade_cursor_manager is not None:
        trade_cursors = await trade_cursor_manager.attach_message_for_intent(
            message,
            intent,
            hypothesis.intent_type,
            candidates=context.active_trade_cursors,
            lifecycle_strategy=(
                lifecycle_strategy if transition_requested else None
            ),
        )
    approved_request = request.model_copy(
        update={"trade_cursor_ids": [cursor.cursor_id for cursor in trade_cursors]}
    )
    if telegram_deduplicator is not None:
        telegram_deduplicator.mark_delivered(message)
    return approved_request


def select_strategy_tier_for_market(
    message: TelegramMessageEnvelope,
    candidates: QwenStrategyCandidateSet,
    reviews: Mapping[StrategyTier, FilterDecision],
    active_trade_cursors: list[TradeThreadCursor],
    *,
    selected_strategy_tier: StrategyTier | None = None,
) -> StrategyTier | None:
    """Return Ministral's approved tier whose market snapshot the Flow must load."""
    filter_decisions = {
        tier: (candidates.candidates[tier], decision)
        for tier, decision in reviews.items()
        if decision.status == "approved" and decision.canonical_intent is not None
    }
    if not filter_decisions:
        return None
    lifecycle_cursors = _matching_lifecycle_cursors(
        filter_decisions,
        active_trade_cursors,
    )
    return _resolve_strategy_tier(
        message,
        selected_strategy_tier,
        filter_decisions,
        lifecycle_cursors,
    )


def _resolve_strategy_tier(
    message: TelegramMessageEnvelope,
    selected_strategy_tier: StrategyTier | None,
    filter_decisions: Mapping[
        StrategyTier,
        tuple[QwenSignalHypothesis, FilterDecision],
    ],
    lifecycle_cursors: list[TradeThreadCursor],
) -> StrategyTier | None:
    inherited_strategy = _shared_lifecycle_strategy(lifecycle_cursors)
    transition_requested = (
        inherited_strategy is not None
        and message.strategy_tier_hint is not None
        and message.strategy_tier_hint != inherited_strategy.strategy_tier
    )
    if inherited_strategy is not None and not transition_requested:
        if inherited_strategy.strategy_tier in filter_decisions:
            return inherited_strategy.strategy_tier
        return None
    if transition_requested:
        selected_strategy_tier = message.strategy_tier_hint
    if selected_strategy_tier in filter_decisions:
        return selected_strategy_tier
    return None


def _score_confidence(
    message: TelegramMessageEnvelope,
    source_confidence: float,
    selected_strategy_tier: StrategyTier,
    filter_decisions: Mapping[
        StrategyTier,
        tuple[QwenSignalHypothesis, FilterDecision],
    ],
    lifecycle_cursors: list[TradeThreadCursor],
    performance_snapshot: PerformanceMetricsSnapshot | None,
) -> ConfidenceDecision:
    inherited_strategy = _shared_lifecycle_strategy(lifecycle_cursors)
    transition_requested = (
        inherited_strategy is not None
        and message.strategy_tier_hint is not None
        and message.strategy_tier_hint != inherited_strategy.strategy_tier
    )
    if inherited_strategy is not None and not transition_requested:
        return _confidence_from_lifecycle(inherited_strategy)

    _, selected_review = filter_decisions[selected_strategy_tier]
    confidence = evaluate_confidence(
        source_confidence,
        selected_strategy_tier=selected_strategy_tier,
        quality_score=selected_review.quality_score,
        performance=performance_snapshot,
    )
    if transition_requested:
        confidence = confidence.model_copy(
            update={
                "strategy_tier": message.strategy_tier_hint,
                "reasons": [
                    *confidence.reasons,
                    "explicit_parent_linked_telegram_strategy_transition",
                ],
            }
        )
    return confidence


def _market_snapshot_for_stop_loss(
    hypothesis: QwenSignalHypothesis,
    market_snapshot: MarketAnalysisSnapshot | None,
    market_snapshots: Mapping[ExchangeId, MarketExecutionSnapshot] | None,
) -> MarketAnalysisSnapshot | None:
    if market_snapshots is not None and hypothesis.symbol is not None:
        for snapshot in market_snapshots.values():
            if snapshot.market.symbol.upper() == hypothesis.symbol.upper():
                return snapshot.market
    return market_snapshot


def _snapshot_rejection_reasons(
    snapshot: MarketExecutionSnapshot,
    *,
    exchange_id: ExchangeId,
    network: ExchangeNetwork,
    symbol: str,
    reference_price: Decimal,
    intent_type: IntentType,
) -> list[str]:
    reasons = list(snapshot.rejection_reasons)
    if snapshot.market.exchange_id != exchange_id:
        reasons.append("market_snapshot_exchange_mismatch")
    if snapshot.market.network != network:
        reasons.append("market_snapshot_network_mismatch")
    try:
        validate_market_snapshot(
            snapshot_symbol=snapshot.market.symbol,
            requested_symbol=symbol,
            snapshot_reference_price=snapshot.reference_price,
            reference_price=reference_price,
            current_price=snapshot.market.current_price,
        )
    except ValueError as exc:
        reasons.append(str(exc))
    funding_rate_decision = evaluate_funding_rate_cycle_filter(
        exchange_id=exchange_id,
        network=network,
        symbol=symbol,
        intent_type=intent_type,
        observed_at=snapshot.market.observed_at,
        annualized_funding_rate_fraction=(
            snapshot.annualized_funding_rate_fraction
        ),
    )
    reasons.extend(funding_rate_decision.reasons)
    return reasons


async def _infer_hypotheses(
    qwen_agent: QwenCandidateInferenceAPI | LegacySignalInferenceAPI,
    message: TelegramMessageEnvelope,
    context: TelegramPromptContext,
) -> tuple[list[QwenSignalHypothesis], float, bool]:
    infer_candidates = getattr(qwen_agent, "infer_strategy_candidates", None)
    if callable(infer_candidates):
        candidate_set = await infer_candidates(message, context)
        return (
            [candidate_set.candidates[tier] for tier in StrategyTier],
            candidate_set.interpretation_confidence,
            True,
        )

    hypothesis = await qwen_agent.infer_signal(message, context)
    return [hypothesis], hypothesis.confidence, False


def _matching_lifecycle_cursors(
    decisions: Mapping[
        StrategyTier,
        tuple[QwenSignalHypothesis, FilterDecision],
    ],
    cursors: list[TradeThreadCursor],
) -> list[TradeThreadCursor]:
    matches: dict[str, TradeThreadCursor] = {}
    for hypothesis, decision in decisions.values():
        intent = decision.canonical_intent
        if hypothesis.intent_type == IntentType.NEW_ORDER or intent is None:
            continue
        for cursor in cursors:
            if _cursor_matches_intent(cursor, intent):
                matches[cursor.cursor_id] = cursor
    return list(matches.values())


def _shared_lifecycle_strategy(
    cursors: list[TradeThreadCursor],
) -> PositionLifecycleStrategy | None:
    if not cursors:
        return None
    strategy = cursors[0].lifecycle_strategy
    if any(cursor.lifecycle_strategy != strategy for cursor in cursors[1:]):
        raise ValueError(
            "parent-linked exchange cursors have divergent lifecycle strategies"
        )
    return strategy


def _confidence_from_lifecycle(
    strategy: PositionLifecycleStrategy,
) -> ConfidenceDecision:
    return ConfidenceDecision(
        confidence=strategy.confidence,
        strategy_tier=strategy.strategy_tier,
        source_confidence=strategy.source_confidence,
        quality_score=strategy.quality_score,
        performance_score=strategy.performance_score,
        formula_version=strategy.formula_version,
        reasons=list(strategy.reasons),
    )


def _sizing_from_lifecycle(
    intent: CanonicalTradeIntent,
    strategy: PositionLifecycleStrategy,
) -> PositionSizingDecision:
    return PositionSizingDecision(
        owner_id=intent.owner_id,
        channel_id=intent.channel_id,
        asset_group=intent.asset_group,
        strategy_tier=strategy.strategy_tier,
        owner_weight=strategy.owner_weight,
        asset_group_weight=strategy.asset_group_weight,
        final_position_notional_usd=strategy.position_notional_usd,
        leverage=strategy.leverage,
    )


def _new_lifecycle_strategy(
    message: TelegramMessageEnvelope,
    confidence: ConfidenceDecision,
    sizing: PositionSizingDecision,
    *,
    previous: PositionLifecycleStrategy | None,
) -> PositionLifecycleStrategy:
    transition = previous is not None
    return PositionLifecycleStrategy(
        strategy_tier=confidence.strategy_tier,
        confidence=confidence.confidence,
        source_confidence=confidence.source_confidence,
        quality_score=confidence.quality_score,
        performance_score=confidence.performance_score,
        formula_version=confidence.formula_version,
        owner_weight=sizing.owner_weight,
        asset_group_weight=sizing.asset_group_weight,
        position_notional_usd=sizing.final_position_notional_usd,
        leverage=sizing.leverage,
        source=(
            LifecycleStrategySource.TELEGRAM_TRANSITION
            if transition
            else LifecycleStrategySource.INITIAL_CONFIDENCE
        ),
        source_telegram_message_id=message.telegram_message_id,
        selected_at=message.received_at,
        revision=previous.revision + 1 if transition else 0,
        reasons=list(confidence.reasons),
    )


def _direction_for_action(action: TradeAction) -> PositionDirection:
    if action in (
        TradeAction.OPEN_LONG,
        TradeAction.CLOSE_LONG,
        TradeAction.REDUCE_LONG,
    ):
        return PositionDirection.LONG
    return PositionDirection.SHORT


def _cursor_matches_intent(
    cursor: TradeThreadCursor,
    intent: CanonicalTradeIntent,
) -> bool:
    return (
        cursor.exchange_id in intent.target_exchanges
        and cursor.network == intent.execution_network
        and cursor.symbol.upper() == intent.symbol.upper()
        and cursor.direction == _direction_for_action(intent.action)
    )


def _default_risk_limit(
    message: TelegramMessageEnvelope,
    exchange_id: ExchangeId,
    network: ExchangeNetwork,
    symbol: str,
) -> PairRiskLimit:
    """Non-production default used until owner/pair limits are loaded from policy."""
    return PairRiskLimit(
        owner_id=message.owner_id,
        exchange_id=exchange_id,
        network=network,
        symbol=symbol.upper(),
        maximum_cumulative_position_notional_usd=Decimal("1000"),
        maximum_leverage=5,
        policy_version="scaffold-default-v1",
    )
