"""Draft end-to-end orchestration boundary."""

from __future__ import annotations

from decimal import Decimal

from agentic_perp_trading_bot.confidence_engine.policy import evaluate_confidence
from agentic_perp_trading_bot.performance_engine.weight_engine import compute_position_size
from agentic_perp_trading_bot.schemas import (
    ApprovedExecutionRequest,
    MarketAnalysisSnapshot,
    TelegramMessageEnvelope,
    TelegramPromptContext,
)
from agentic_perp_trading_bot.skills_api import MinistralFilterAPI, OwnerQwenAPI
from agentic_perp_trading_bot.telegram_ingestion.deduplication import InMemoryTelegramDeduplicator


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
) -> ApprovedExecutionRequest | None:
    """Run one normalized message through confidence-based backtest stages."""
    if telegram_deduplicator is not None:
        input_deduplication = telegram_deduplicator.check(message)
        if input_deduplication.is_duplicate:
            return None

    context = prompt_context or TelegramPromptContext.from_message(message)
    hypothesis = await qwen_agent.infer_signal(message, context)
    hypothesis.source_dedup_key = message.dedup_key
    filter_decision = await filter_agent.review(hypothesis, context, market_snapshot)
    if filter_decision.status != "approved" or filter_decision.canonical_intent is None:
        return None

    canonical_intent = filter_decision.canonical_intent
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

    confidence = evaluate_confidence(
        hypothesis.confidence,
        pair_blacklisted=pair_blacklisted,
        instant_order=canonical_intent.order_type == "market",
        current_price=effective_current_price,
        reference_price=reference_price,
        symbol=canonical_intent.symbol,
        asset_group=canonical_intent.asset_group,
        tradfi_perpetual_pair=tradfi_perpetual_pair,
    )
    if not confidence.approved:
        return None

    intent = canonical_intent.model_copy(
        update={"strategy_tier": confidence.strategy_tier}
    )
    sizing = compute_position_size(
        filter_decision.model_copy(update={"canonical_intent": intent})
    )
    return ApprovedExecutionRequest(
        intent=intent,
        sizing=sizing,
        confidence=confidence,
        idempotency_key=message.dedup_key or f"{message.channel_id}:{message.telegram_message_id}",
    )
