"""Draft end-to-end orchestration boundary."""

from __future__ import annotations

from agentic_perp_trading_bot.ministral_filter.filter_agent import MinistralFilterAgent
from agentic_perp_trading_bot.performance_engine.weight_engine import compute_position_size
from agentic_perp_trading_bot.qwen_agents.owner_agent import OwnerQwenAgent
from agentic_perp_trading_bot.risk_engine.policy import evaluate_risk
from agentic_perp_trading_bot.schemas import ApprovedExecutionRequest, TelegramMessageEnvelope


async def process_message(
    message: TelegramMessageEnvelope,
    qwen_agent: OwnerQwenAgent,
    filter_agent: MinistralFilterAgent,
) -> ApprovedExecutionRequest | None:
    """Run one Telegram message through QWEN, Ministral, sizing, and risk."""
    hypothesis = await qwen_agent.infer_signal(message)
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
        idempotency_key=f"{message.channel_id}:{message.telegram_message_id}",
    )
