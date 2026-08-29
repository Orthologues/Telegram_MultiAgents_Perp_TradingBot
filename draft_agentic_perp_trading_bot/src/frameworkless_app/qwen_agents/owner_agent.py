"""Draft owner-specific QWEN agent and shared-skill interface.

Each owner agent consumes Chinese Telegram text/images plus manual RAG JSON
profiles. It returns reviewable JSON decisions only and must not call exchange
tools.
"""

from __future__ import annotations

import json
from pathlib import Path

from agentic_perp_trading_bot.schemas import (
    IntentType,
    OwnerRagProfile,
    PositionReductionHypothesis,
    QwenSignalHypothesis,
    QwenStrategyCandidateSet,
    StrategyTier,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradingMessageSynonymDecision,
)


class OwnerQwenAgent:
    def __init__(
        self,
        owner_profile_path: str,
        model_id: str = "qwen3-vl-235b-a22",
    ):
        self.owner_profile_path = owner_profile_path
        self.model_id = model_id

    def load_rag_profile(self) -> OwnerRagProfile:
        """Load and validate the owner JSON profile before model integration."""
        profile_path = Path(self.owner_profile_path)
        return OwnerRagProfile.model_validate(
            json.loads(profile_path.read_text(encoding="utf-8"))
        )

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
        """Return the intermediate candidate for compatibility with focused skills."""
        candidates = await self.infer_strategy_candidates(message, prompt_context)
        return candidates.candidates[StrategyTier.INTERMEDIATE]

    async def infer_strategy_candidates(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext | None = None,
    ) -> QwenStrategyCandidateSet:
        """Infer one reviewable candidate for each architecture strategy tier."""
        context = prompt_context or TelegramPromptContext.from_message(message)
        if context.current_message.telegram_message_id != message.telegram_message_id:
            raise ValueError("prompt context current message does not match QWEN input")
        _ = self.build_prompt_messages(context)
        return QwenStrategyCandidateSet(
            owner_id=message.owner_id,
            channel_id=message.channel_id,
            asset_group=message.asset_group,
            model_id=self.model_id,
            interpretation_confidence=0.0,
            candidates={
                tier: QwenSignalHypothesis(
                    owner_id=message.owner_id,
                    channel_id=message.channel_id,
                    asset_group=message.asset_group,
                    model_id=self.model_id,
                    strategy_tier=tier,
                    intent_type=IntentType.IGNORE,
                    confidence=0.0,
                    evidence=[],
                    ambiguities=["placeholder implementation"],
                    source_dedup_key=message.dedup_key,
                )
                for tier in StrategyTier
            },
            source_dedup_key=message.dedup_key,
        )

    async def infer_synonym(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
    ) -> TradingMessageSynonymDecision:
        """Run the shared trading-message synonym skill for this owner."""
        if prompt_context.current_message.telegram_message_id != message.telegram_message_id:
            raise ValueError("prompt context current message does not match input")
        return TradingMessageSynonymDecision(
            owner_id=message.owner_id,
            channel_id=message.channel_id,
            telegram_message_id=message.telegram_message_id,
            confidence=0.0,
            reasons=["placeholder implementation; authentic serial RAG is pending"],
            needs_human_review=True,
        )

    async def infer_position_reduction(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
    ) -> PositionReductionHypothesis:
        """Interpret a reduce-and-protect message without creating an order."""
        if prompt_context.current_message.telegram_message_id != message.telegram_message_id:
            raise ValueError("prompt context current message does not match input")
        _ = self.build_prompt_messages(prompt_context)
        return PositionReductionHypothesis(
            owner_id=message.owner_id,
            channel_id=message.channel_id,
            telegram_message_id=message.telegram_message_id,
            confidence=0.0,
            ambiguities=[
                "placeholder implementation; live position and order state are required"
            ],
            needs_human_review=True,
        )
