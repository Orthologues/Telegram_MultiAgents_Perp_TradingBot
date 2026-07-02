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
)


class OwnerQwenAgent:
    def __init__(self, owner_profile_path: str):
        self.owner_profile_path = owner_profile_path

    async def infer_signal(self, message: TelegramMessageEnvelope) -> QwenSignalHypothesis:
        """Call AWS Bedrock QWEN multimodal inference in the real implementation."""
        return QwenSignalHypothesis(
            owner_id=message.owner_id,
            channel_id=message.channel_id,
            asset_group=message.asset_group,
            strategy_tier=message.strategy_tier_hint or StrategyTier.INTERMEDIATE,
            intent_type=IntentType.IGNORE,
            confidence=0.0,
            evidence=[],
            ambiguities=["placeholder implementation"],
        )
