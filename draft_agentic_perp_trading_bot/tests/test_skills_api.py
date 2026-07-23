import asyncio
from datetime import datetime, timezone

from agentic_perp_trading_bot.qwen_agents.owner_agent import OwnerQwenAgent
from agentic_perp_trading_bot.schemas import (
    AssetGroup,
    OwnerId,
    TelegramMessageEnvelope,
    TelegramPromptContext,
)
from agentic_perp_trading_bot.skills_api import (
    MinistralFilterAPI,
    OwnerQwenAPI,
    TelegramAgentAPI,
)


def test_skills_api_exports_explicit_agent_contracts() -> None:
    assert {
        TelegramAgentAPI.__name__,
        OwnerQwenAPI.__name__,
        MinistralFilterAPI.__name__,
    } == {
        "TelegramAgentAPI",
        "OwnerQwenAPI",
        "MinistralFilterAPI",
    }


def _message() -> TelegramMessageEnvelope:
    return TelegramMessageEnvelope(
        owner_id=OwnerId.OWNER_A_SHU_QIN,
        channel_id="owner_a_channel_a",
        asset_group=AssetGroup.MIXED,
        telegram_message_id="123",
        received_at=datetime.now(timezone.utc),
        raw_text="ETH 多",
    )


def test_synonym_inference_returns_a_reviewable_decision() -> None:
    message = _message()
    context = TelegramPromptContext.from_message(message)
    decision = asyncio.run(
        OwnerQwenAgent("owner_a.json").infer_synonym(
            message,
            context,
        )
    )

    assert decision.telegram_message_id == "123"
    assert decision.confidence == 0.0
    assert decision.needs_human_review is True
