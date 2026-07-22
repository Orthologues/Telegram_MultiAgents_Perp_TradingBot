"""Draft owner-specific QWEN agent interface.

Each owner agent consumes Chinese Telegram text/images plus manual RAG JSON profiles
and returns a JSON trading hypothesis only. It must not call exchange tools.
"""

from __future__ import annotations

from agentic_perp_trading_bot.schemas import (
    IntentType,
    QwenSignalHypothesis,
    StrategyTier,
    TelegramMessageEnvelope,
    TelegramPromptContext,
)


class OwnerQwenAgent:
    def __init__(self, owner_profile_path: str):
        self.owner_profile_path = owner_profile_path

    def build_prompt_messages(
        self,
        prompt_context: TelegramPromptContext,
    ) -> list[dict[str, object]]:
        return prompt_context.to_prompt_messages()

    async def infer_signal(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext | None = None,
    ) -> QwenSignalHypothesis:
        """Call AWS Bedrock QWEN multimodal inference in the real implementation."""
        context = prompt_context or TelegramPromptContext.from_message(message)
        if context.current_message.telegram_message_id != message.telegram_message_id:
            raise ValueError("prompt context current message does not match QWEN input")
        _ = self.build_prompt_messages(context)
        return QwenSignalHypothesis(
            owner_id=message.owner_id,
            channel_id=message.channel_id,
            asset_group=message.asset_group,
            strategy_tier=message.strategy_tier_hint or StrategyTier.INTERMEDIATE,
            intent_type=IntentType.IGNORE,
            confidence=0.0,
            evidence=[],
            ambiguities=["placeholder implementation"],
            source_dedup_key=message.dedup_key,
        )
