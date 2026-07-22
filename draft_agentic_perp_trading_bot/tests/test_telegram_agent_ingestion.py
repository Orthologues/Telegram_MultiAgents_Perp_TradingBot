import asyncio
from datetime import datetime, timezone

import pytest

from agentic_perp_trading_bot.schemas import (
    IngestionTransport,
    OwnerId,
    TelegramAgentChannelConfig,
    TelegramAgentRetrievalBatch,
)
from agentic_perp_trading_bot.telegram_ingestion.agent_worker import (
    CallableTelegramAgentRetriever,
    InMemoryTelegramCursorStore,
    TelegramAgentPoller,
)
from agentic_perp_trading_bot.telegram_ingestion.normalizer import (
    attach_archived_media,
    normalize_telegram_agent_message,
)
from agentic_perp_trading_bot.telegram_ingestion.pipeline import (
    BedrockInputPublisher,
    TelegramIngestionPipeline,
)
from agentic_perp_trading_bot.telegram_ingestion.reply_tree import (
    InMemoryReplyTreeIndexRegistry,
)
from agentic_perp_trading_bot.telegram_ingestion.storage import (
    InMemoryMessageMetadataRepository,
    InMemoryRawMediaArchive,
)


def _retrieved_message(
    message_id: str,
    *,
    text: str = "ETH 多",
    media: bool = False,
    reply_to_msg_id: str | None = None,
) -> dict:
    return {
        "id": message_id,
        "date": "2026-07-20T09:30:00+00:00",
        "from_id": "PeerUser(user_id=42)",
        "text": text,
        "reply_to_msg_id": reply_to_msg_id,
        "forward_from": None,
        "edit_date": None,
        "media": media,
        "entities": None,
    }


def test_telegram_agent_normalizer_preserves_retrieval_provenance() -> None:
    observed_at = datetime(2026, 7, 20, 9, 31, tzinfo=timezone.utc)

    envelope = normalize_telegram_agent_message(
        _retrieved_message("123", media=True),
        channel_id="owner_a_channel_a",
        telegram_chat_id="-1001234567890",
        retrieval_cursor="122",
        observed_at=observed_at,
    )

    assert envelope.owner_id == OwnerId.OWNER_A_SHU_QIN
    assert envelope.source_transport == IngestionTransport.AG2_TELEGRAM_AGENT
    assert envelope.telegram_chat_id == "-1001234567890"
    assert envelope.telegram_message_id == "123"
    assert envelope.retrieval_cursor == "122"
    assert envelope.source_timestamp == datetime(2026, 7, 20, 9, 30, tzinfo=timezone.utc)
    assert envelope.received_at == observed_at
    assert envelope.raw_media_present is True
    assert envelope.parent_messages == []


def test_normalizer_preserves_direct_parent_message_id() -> None:
    envelope = normalize_telegram_agent_message(
        _retrieved_message("123", reply_to_msg_id="121"),
        channel_id="owner_a_channel_a",
        telegram_chat_id="-1001234567890",
    )

    assert envelope.reply_to_message_id == "121"
    assert envelope.parent_messages == ["121"]


def test_unhydrated_media_messages_do_not_share_an_exact_dedup_key() -> None:
    first = normalize_telegram_agent_message(
        _retrieved_message("123", media=True),
        channel_id="owner_a_channel_a",
        telegram_chat_id="-1001234567890",
    )
    second = normalize_telegram_agent_message(
        _retrieved_message("124", media=True),
        channel_id="owner_a_channel_a",
        telegram_chat_id="-1001234567890",
    )

    assert first.dedup_key != second.dedup_key

    archived_first = attach_archived_media(
        first,
        media_s3_uri="s3://telegram-raw/chart-123.png",
        media_hashes=["same-image-sha256"],
    )
    archived_second = attach_archived_media(
        second,
        media_s3_uri="s3://telegram-raw/chart-124.png",
        media_hashes=["same-image-sha256"],
    )

    assert archived_first.dedup_key == archived_second.dedup_key


def test_text_hash_shortcut_requires_byte_identical_text() -> None:
    first = normalize_telegram_agent_message(
        _retrieved_message("123", text="ETH 多"),
        channel_id="owner_a_channel_a",
        telegram_chat_id="-1001234567890",
    )
    second = normalize_telegram_agent_message(
        _retrieved_message("124", text=" ETH 多 "),
        channel_id="owner_a_channel_a",
        telegram_chat_id="-1001234567890",
    )

    assert first.content_hash != second.content_hash
    assert first.dedup_key != second.dedup_key


def test_poller_reads_after_cursor_and_commits_only_after_processing() -> None:
    calls: list[tuple[str | None, int | None]] = []

    async def retrieve(
        *, messages_since: str | None, maximum_messages: int | None
    ) -> dict:
        calls.append((messages_since, maximum_messages))
        return {
            "message_count": 2,
            "messages": [_retrieved_message("102"), _retrieved_message("101")],
            "start_time": messages_since or "latest",
        }

    async def scenario() -> None:
        retriever = CallableTelegramAgentRetriever(
            telegram_chat_id="-1001234567890",
            retrieve=retrieve,
        )
        cursor_store = InMemoryTelegramCursorStore({"owner_a_channel_a": "100"})
        poller = TelegramAgentPoller(
            retrievers={"owner_a_channel_a": retriever},
            cursor_store=cursor_store,
        )
        config = TelegramAgentChannelConfig(
            channel_id="owner_a_channel_a",
            telegram_chat_id="-1001234567890",
            maximum_messages=50,
        )

        batch = await poller.poll_once(config)

        assert calls == [("100", 50)]
        assert [message.telegram_message_id for message in batch.messages] == ["101", "102"]
        assert batch.previous_cursor == "100"
        assert batch.next_cursor == "102"
        assert await cursor_store.load("owner_a_channel_a") == "100"

        await poller.commit(batch)

        assert await cursor_store.load("owner_a_channel_a") == "102"

    asyncio.run(scenario())


def test_callable_retriever_rejects_inconsistent_ag2_count() -> None:
    async def retrieve(
        *, messages_since: str | None, maximum_messages: int | None
    ) -> dict:
        return {
            "message_count": 2,
            "messages": [_retrieved_message("101")],
            "start_time": messages_since or "latest",
        }

    async def scenario() -> None:
        retriever = CallableTelegramAgentRetriever(
            telegram_chat_id="-1001234567890",
            retrieve=retrieve,
        )

        with pytest.raises(ValueError, match="message_count"):
            await retriever.retrieve_messages(messages_since="100", maximum_messages=50)

    asyncio.run(scenario())


def test_retriever_selects_only_the_agent_retrieve_tool() -> None:
    send_called = False

    async def send(**kwargs) -> str:
        nonlocal send_called
        send_called = True
        return "sent"

    async def retrieve(**kwargs) -> dict:
        return {
            "message_count": 1,
            "messages": [_retrieved_message("101")],
            "start_time": kwargs.get("messages_since") or "latest",
        }

    class FakeTool:
        def __init__(self, name: str, func) -> None:
            self.name = name
            self.func = func

    class FakeTelegramAgent:
        tools = [FakeTool("telegram_send", send), FakeTool("telegram_retrieve", retrieve)]

    async def scenario() -> None:
        retriever = CallableTelegramAgentRetriever.from_telegram_agent(
            telegram_chat_id="-1001234567890",
            telegram_agent=FakeTelegramAgent(),
        )
        batch = await retriever.retrieve_messages(messages_since="100", maximum_messages=50)

        assert [message.id for message in batch.messages] == ["101"]
        assert send_called is False

    asyncio.run(scenario())


def test_retrieval_batch_validates_message_count() -> None:
    with pytest.raises(ValueError, match="message_count"):
        TelegramAgentRetrievalBatch.model_validate(
            {
                "telegram_chat_id": "-1001234567890",
                "message_count": 2,
                "messages": [_retrieved_message("101")],
                "start_time": "100",
            }
        )


def test_pipeline_persists_records_and_publishes_only_unique_messages() -> None:
    async def retrieve(
        *, messages_since: str | None, maximum_messages: int | None
    ) -> dict:
        return {
            "message_count": 2,
            "messages": [_retrieved_message("101"), _retrieved_message("102")],
            "start_time": messages_since or "latest",
        }

    published: list[str] = []

    async def publish(context) -> None:
        published.append(context.current_message.telegram_message_id)

    async def scenario() -> None:
        retriever = CallableTelegramAgentRetriever(
            telegram_chat_id="-1001234567890",
            retrieve=retrieve,
        )
        cursor_store = InMemoryTelegramCursorStore()
        poller = TelegramAgentPoller(
            retrievers={"owner_a_channel_a": retriever},
            cursor_store=cursor_store,
        )
        metadata = InMemoryMessageMetadataRepository()
        pipeline = TelegramIngestionPipeline(
            poller=poller,
            raw_media_archive=InMemoryRawMediaArchive(),
            metadata_repository=metadata,
            bedrock_publisher=BedrockInputPublisher(publish),
        )

        config = TelegramAgentChannelConfig(
            channel_id="owner_a_channel_a",
            telegram_chat_id="-1001234567890",
            maximum_messages=50,
        )
        processed = await pipeline.process_once(config)

        assert [message.telegram_message_id for message in processed] == ["101"]
        assert published == ["101"]
        assert [record.message.telegram_message_id for record in metadata.records] == [
            "101",
            "102",
        ]
        assert await cursor_store.load("owner_a_channel_a") == "102"

    asyncio.run(scenario())


def test_pipeline_expands_parent_messages_in_chronological_order() -> None:
    async def retrieve(
        *, messages_since: str | None, maximum_messages: int | None
    ) -> dict:
        return {
            "message_count": 3,
            "messages": [
                _retrieved_message("103", text="close", reply_to_msg_id="102"),
                _retrieved_message("102", text="add", reply_to_msg_id="101"),
                _retrieved_message("101", text="open"),
            ],
            "start_time": messages_since or "latest",
        }

    published = []

    async def publish(context) -> None:
        published.append(context)

    async def scenario() -> None:
        retriever = CallableTelegramAgentRetriever(
            telegram_chat_id="-1001234567890",
            retrieve=retrieve,
        )
        poller = TelegramAgentPoller(
            retrievers={"owner_a_channel_a": retriever},
            cursor_store=InMemoryTelegramCursorStore(),
        )
        metadata = InMemoryMessageMetadataRepository()
        pipeline = TelegramIngestionPipeline(
            poller=poller,
            raw_media_archive=InMemoryRawMediaArchive(),
            metadata_repository=metadata,
            bedrock_publisher=BedrockInputPublisher(publish),
        )

        await pipeline.process_once(
            TelegramAgentChannelConfig(
                channel_id="owner_a_channel_a",
                telegram_chat_id="-1001234567890",
            )
        )

        assert [context.current_message.telegram_message_id for context in published] == [
            "101",
            "102",
            "103",
        ]
        assert published[0].parent_messages == []
        assert published[1].parent_messages[0].telegram_message_id == "101"
        assert [parent.telegram_message_id for parent in published[2].parent_messages] == [
            "101",
            "102",
        ]
        assert [prompt["telegram_message_id"] for prompt in published[2].to_prompt_messages()] == [
            "101",
            "102",
            "103",
        ]
        assert metadata.records[-1].message.parent_messages == ["101", "102"]

    asyncio.run(scenario())


def test_pipeline_traverses_prior_sibling_replies() -> None:
    async def retrieve(
        *, messages_since: str | None, maximum_messages: int | None
    ) -> dict:
        return {
            "message_count": 3,
            "messages": [
                _retrieved_message("103", text="C", reply_to_msg_id="101"),
                _retrieved_message("102", text=None, media=True, reply_to_msg_id="101"),
                _retrieved_message("101", text="A"),
            ],
            "start_time": messages_since or "latest",
        }

    published = []

    async def publish(context) -> None:
        published.append(context)

    async def scenario() -> None:
        retriever = CallableTelegramAgentRetriever(
            telegram_chat_id="-1001234567890",
            retrieve=retrieve,
        )
        poller = TelegramAgentPoller(
            retrievers={"owner_a_channel_a": retriever},
            cursor_store=InMemoryTelegramCursorStore(),
        )
        metadata = InMemoryMessageMetadataRepository()
        pipeline = TelegramIngestionPipeline(
            poller=poller,
            raw_media_archive=InMemoryRawMediaArchive(),
            metadata_repository=metadata,
            bedrock_publisher=BedrockInputPublisher(publish),
        )

        await pipeline.process_once(
            TelegramAgentChannelConfig(
                channel_id="owner_a_channel_a",
                telegram_chat_id="-1001234567890",
            )
        )

        assert published[-1].current_message.telegram_message_id == "103"
        assert [parent.telegram_message_id for parent in published[-1].parent_messages] == [
            "101",
            "102",
        ]
        assert [prompt["role"] for prompt in published[-1].to_prompt_messages()] == [
            "parent",
            "parent",
            "current",
        ]
        assert metadata.records[-1].message.parent_messages == ["101", "102"]

    asyncio.run(scenario())


def test_reply_tree_index_is_scoped_to_each_owner_qwen_agent() -> None:
    registry = InMemoryReplyTreeIndexRegistry()
    owner_a_index = registry.for_owner(OwnerId.OWNER_A_SHU_QIN)

    root = normalize_telegram_agent_message(
        _retrieved_message("100", text="A"),
        channel_id="owner_a_channel_a",
        telegram_chat_id="-1001234567890",
    )
    sibling = normalize_telegram_agent_message(
        _retrieved_message("101", text="B", reply_to_msg_id="100"),
        channel_id="owner_a_channel_a",
        telegram_chat_id="-1001234567890",
    )
    current_owner_a = normalize_telegram_agent_message(
        _retrieved_message("102", text="C", reply_to_msg_id="100"),
        channel_id="owner_a_channel_a",
        telegram_chat_id="-1001234567890",
    )
    current_owner_b = normalize_telegram_agent_message(
        _retrieved_message("102", text="C", reply_to_msg_id="100"),
        channel_id="owner_b_channel_a",
        telegram_chat_id="-1001234567890",
    )

    owner_a_index.add(root)
    owner_a_index.add(sibling)

    assert owner_a_index.parent_messages_for(current_owner_a) == ["100", "101"]
    assert registry.for_owner(OwnerId.OWNER_B_LAO_TU).parent_messages_for(current_owner_b) == [
        "100"
    ]
