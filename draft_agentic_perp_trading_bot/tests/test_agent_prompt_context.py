from frameworkless_app.ministral_filter.filter_agent import MinistralFilterAgent
from frameworkless_app.qwen_agents.owner_agent import OwnerQwenAgent
from frameworkless_app.schemas import (
    AssetGroup,
    IntentType,
    OwnerId,
    QwenSignalHypothesis,
    StrategyTier,
    TelegramPromptContext,
    TelegramPromptMessage,
)
from frameworkless_app.telegram_ingestion.normalizer import (
    normalize_telegram_agent_message,
)


def test_qwen_and_ministral_receive_the_same_id_labeled_serial_context() -> None:
    current = normalize_telegram_agent_message(
        {
            "id": "103",
            "date": "2026-07-20T09:30:00+00:00",
            "from_id": "PeerUser(user_id=42)",
            "text": "C",
            "reply_to_msg_id": "101",
            "forward_from": None,
            "edit_date": None,
            "media": False,
            "entities": None,
        },
        channel_id="owner_a_channel_a",
        telegram_chat_id="-1001234567890",
    )
    context = TelegramPromptContext.from_message(
        current,
        [
            TelegramPromptMessage(telegram_message_id="101", raw_text="A"),
            TelegramPromptMessage(telegram_message_id="102", raw_text="B", raw_media_present=True),
        ],
    )
    hypothesis = QwenSignalHypothesis(
        owner_id=OwnerId.OWNER_A_SHU_QIN,
        channel_id="owner_a_channel_a",
        asset_group=AssetGroup.MIXED,
        strategy_tier=StrategyTier.INTERMEDIATE,
        intent_type=IntentType.IGNORE,
        confidence=0.0,
    )

    qwen_prompt = OwnerQwenAgent("owner_a.json").build_prompt_messages(context)
    ministral_prompt = MinistralFilterAgent("ministral-3-8b").build_prompt_messages(
        hypothesis,
        context,
    )

    assert [message["telegram_message_id"] for message in qwen_prompt] == [
        "101",
        "102",
        "103",
    ]
    assert qwen_prompt[-1]["parent_message_ids"] == ["101", "102"]
    assert [message["telegram_message_id"] for message in ministral_prompt[:-1]] == [
        "101",
        "102",
        "103",
    ]
    assert ministral_prompt[-1]["role"] == "qwen_hypothesis"
