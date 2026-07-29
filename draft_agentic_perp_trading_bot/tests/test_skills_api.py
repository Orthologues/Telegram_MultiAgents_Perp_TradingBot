import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from agentic_perp_trading_bot.qwen_agents.owner_agent import OwnerQwenAgent
from agentic_perp_trading_bot.schemas import (
    AssetGroup,
    OwnerId,
    StrategyTier,
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
    assert hasattr(OwnerQwenAPI, "infer_position_reduction")
    assert hasattr(OwnerQwenAPI, "infer_strategy_candidates")
    assert hasattr(MinistralFilterAPI, "protect_entry_after_take_profit")
    assert hasattr(MinistralFilterAPI, "record_execution_event")


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


def test_owner_qwen_exposes_exactly_five_strategy_candidates() -> None:
    message = _message()
    candidates = asyncio.run(
        OwnerQwenAgent("owner_a.json").infer_strategy_candidates(
            message,
            TelegramPromptContext.from_message(message),
        )
    )

    assert list(candidates.candidates) == list(StrategyTier)
    assert {
        candidate.strategy_tier for candidate in candidates.candidates.values()
    } == set(StrategyTier)


def test_owner_qwen_loads_typed_rag_profile_provenance() -> None:
    profile_path = (
        Path(__file__).parents[1]
        / "rag_profiles"
        / "owner_a_shu_qin"
        / "shared_style.json"
    )
    profile = OwnerQwenAgent(str(profile_path)).load_rag_profile()

    assert profile.owner_id == OwnerId.OWNER_A_SHU_QIN
    assert profile.s3_archive_prefix.startswith("s3://")
    assert profile.serial_rag_examples == []


def test_position_reduction_skill_returns_bounded_reviewable_hypothesis() -> None:
    message = _message()
    context = TelegramPromptContext.from_message(message)
    decision = asyncio.run(
        OwnerQwenAgent("owner_a.json").infer_position_reduction(
            message,
            context,
        )
    )

    assert decision.telegram_message_id == "123"
    assert decision.selected_reduction_fraction is None
    assert decision.minimum_reduction_fraction == Decimal("0.30")
    assert decision.maximum_reduction_fraction == Decimal("0.40")
    assert decision.stop_loss_profit_offset_fraction == Decimal("0.0015")
    assert decision.take_profit_labels == ("TP1", "TP2", "TP3")
    assert decision.resize_unfilled_take_profit_orders is True
    assert decision.needs_human_review is True
