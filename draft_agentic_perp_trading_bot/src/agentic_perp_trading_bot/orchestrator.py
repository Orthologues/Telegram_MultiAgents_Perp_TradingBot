"""Draft end-to-end orchestration boundary."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from agentic_perp_trading_bot.confidence_engine.policy import evaluate_confidence
from agentic_perp_trading_bot.performance_engine.weight_engine import compute_position_size
from agentic_perp_trading_bot.risk_engine.policy import evaluate_deterministic_risk
from agentic_perp_trading_bot.schemas import (
    ApprovedExecutionRequest,
    CanonicalTradeIntent,
    ConfidenceDecision,
    ExchangeId,
    FilterDecision,
    IntentType,
    LifecycleStrategySource,
    MarketAnalysisSnapshot,
    PairRiskLimit,
    PerformanceMetricsSnapshot,
    PositionDirection,
    PositionLifecycleStrategy,
    PositionSizingDecision,
    QwenSignalHypothesis,
    StrategyTier,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradeAction,
    TradeThreadCursor,
)
from agentic_perp_trading_bot.skills_api import MinistralFilterAPI, OwnerQwenAPI
from agentic_perp_trading_bot.telegram_ingestion.deduplication import InMemoryTelegramDeduplicator
from agentic_perp_trading_bot.trade_cursor import ConcurrentTradeCursorManager


async def process_message(
    message: TelegramMessageEnvelope,
    qwen_agent: OwnerQwenAPI,
    filter_agent: MinistralFilterAPI,
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
) -> ApprovedExecutionRequest | None:
    """Run one normalized message through five-tier review and deterministic policy."""
    if telegram_deduplicator is not None:
        input_deduplication = telegram_deduplicator.check(message)
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

    if inherited_strategy is not None and not transition_requested:
        confidence = _confidence_from_lifecycle(inherited_strategy)
    else:
        mean_quality = sum(
            decision.quality_score for _, decision in filter_decisions.values()
        ) / len(filter_decisions)
        confidence = evaluate_confidence(
            source_confidence,
            quality_score=mean_quality,
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

    selected = filter_decisions.get(confidence.strategy_tier)
    if selected is None:
        if complete_candidate_set or transition_requested:
            return None
        selected = next(iter(filter_decisions.values()))

    hypothesis, filter_decision = selected
    canonical_intent = filter_decision.canonical_intent
    assert canonical_intent is not None
    if inherited_strategy is not None and not any(
        _cursor_matches_intent(cursor, canonical_intent)
        for cursor in lifecycle_cursors
    ):
        return None
    if (
        canonical_intent.stop_loss is None
        and filter_decision.omitted_stop_loss is not None
    ):
        canonical_intent = canonical_intent.model_copy(
            update={"stop_loss": filter_decision.omitted_stop_loss.stop_loss}
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
    risk_decisions = [
        evaluate_deterministic_risk(
            sizing,
            exchange_id=exchange_id,
            symbol=intent.symbol,
            limits=limits_by_exchange.get(exchange_id)
            or _default_risk_limit(message, exchange_id, intent.symbol),
            existing_position_notional_usdt=current_notional_by_exchange.get(
                exchange_id,
                Decimal("0"),
            ),
            pair_blacklisted=pair_blacklisted,
            instant_order=intent.order_type == "market",
            current_price=effective_current_price,
            reference_price=reference_price,
            asset_group=intent.asset_group,
            tradfi_perpetual_pair=tradfi_perpetual_pair,
        )
        for exchange_id in dict.fromkeys(intent.target_exchanges)
    ]
    if not risk_decisions or any(not decision.approved for decision in risk_decisions):
        return None

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
    return ApprovedExecutionRequest(
        intent=intent,
        sizing=sizing,
        confidence=confidence,
        lifecycle_strategy=lifecycle_strategy,
        risk_decisions=risk_decisions,
        idempotency_key=message.dedup_key or f"{message.channel_id}:{message.telegram_message_id}",
        source_telegram_message_id=message.telegram_message_id,
        parent_message_ids=list(message.parent_messages),
        trade_cursor_ids=[cursor.cursor_id for cursor in trade_cursors],
    )


async def _infer_hypotheses(
    qwen_agent: OwnerQwenAPI,
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
        final_position_notional_usdt=strategy.position_notional_usdt,
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
        position_notional_usdt=sizing.final_position_notional_usdt,
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
        and cursor.symbol.upper() == intent.symbol.upper()
        and cursor.direction == _direction_for_action(intent.action)
    )


def _default_risk_limit(
    message: TelegramMessageEnvelope,
    exchange_id: ExchangeId,
    symbol: str,
) -> PairRiskLimit:
    """Non-production default used until owner/pair limits are loaded from policy."""
    return PairRiskLimit(
        owner_id=message.owner_id,
        exchange_id=exchange_id,
        symbol=symbol.upper(),
        maximum_cumulative_position_notional_usdt=Decimal("1000"),
        maximum_leverage=5,
        policy_version="scaffold-default-v1",
    )
