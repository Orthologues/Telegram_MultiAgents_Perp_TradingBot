"""Draft end-to-end orchestration boundary."""

from __future__ import annotations

from agentic_perp_trading_bot.ministral_filter.filter_agent import MinistralFilterAgent
from agentic_perp_trading_bot.performance_engine.weight_engine import compute_position_size
from agentic_perp_trading_bot.qwen_agents.owner_agent import OwnerQwenAgent
from agentic_perp_trading_bot.risk_engine.policy import evaluate_risk
from agentic_perp_trading_bot.schemas import ApprovedExecutionRequest, TelegramMessageEnvelope
from agentic_perp_trading_bot.telegram_ingestion.deduplication import InMemoryTelegramDeduplicator


async def process_message(
    message: TelegramMessageEnvelope,
    qwen_agent: OwnerQwenAgent,
    filter_agent: MinistralFilterAgent,
    telegram_deduplicator: InMemoryTelegramDeduplicator | None = None,
) -> ApprovedExecutionRequest | None:
    """Run one Telegram message through QWEN, Ministral, sizing, and risk."""
    if telegram_deduplicator is not None:
        input_deduplication = telegram_deduplicator.check(message)
        if input_deduplication.is_duplicate:
            return None

    hypothesis = await qwen_agent.infer_signal(message)
    hypothesis.source_dedup_key = message.dedup_key
    filter_decision = await filter_agent.review(hypothesis)
    if filter_decision.status != "approved" or filter_decision.canonical_intent is None:
        return None

    sizing = compute_position_size(filter_decision)
    risk = evaluate_risk(sizing)
    if not risk.approved:
        return None

    return ApprovedExecutionRequest(
        intent=filter_decision.canonical_intent,
        sizing=sizing,
        risk=risk,
        idempotency_key=message.dedup_key or f"{message.channel_id}:{message.telegram_message_id}",
    )
