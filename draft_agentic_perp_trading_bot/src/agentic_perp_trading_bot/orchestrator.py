"""Draft end-to-end orchestration boundary."""

from __future__ import annotations

from decimal import Decimal

from agentic_perp_trading_bot.confidence_engine.policy import evaluate_confidence
from agentic_perp_trading_bot.performance_engine.weight_engine import compute_position_size
from agentic_perp_trading_bot.schemas import (
    ApprovedExecutionRequest,
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
) -> ApprovedExecutionRequest | None:
    """Run one normalized message through confidence-based backtest stages."""
    if telegram_deduplicator is not None:
        input_deduplication = telegram_deduplicator.check(message)
        if input_deduplication.is_duplicate:
            return None

    context = prompt_context or TelegramPromptContext.from_message(message)
    hypothesis = await qwen_agent.infer_signal(message, context)
    hypothesis.source_dedup_key = message.dedup_key
    filter_decision = await filter_agent.review(hypothesis, context)
    if filter_decision.status != "approved" or filter_decision.canonical_intent is None:
        return None

    confidence = evaluate_confidence(
        hypothesis.confidence,
        pair_blacklisted=pair_blacklisted,
        instant_order=filter_decision.canonical_intent.order_type == "market",
        current_price=current_price,
        reference_price=reference_price,
    )
    if not confidence.approved:
        return None

    intent = filter_decision.canonical_intent.model_copy(
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
