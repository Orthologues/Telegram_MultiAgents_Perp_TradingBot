import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from crewai_app.adapters.aws.persistence.message_labelling import (
    DeferredQwenLabellingQueue,
    DynamoDBMessageLabellingRepository,
    InMemoryMessageLabellingRepository,
)
from crewai_app.domain.contracts.schemas import (
    AssetGroup,
    OwnerId,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradingMessageRelation,
    TradingMessageRelationDecision,
)


def _prompt_context() -> TelegramPromptContext:
    message = TelegramMessageEnvelope(
        owner_id=OwnerId.OWNER_A_SHU_QIN,
        channel_id="owner_a_channel_a",
        asset_group=AssetGroup.MIXED,
        telegram_message_id="1037",
        received_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        raw_text="ETH 多",
    )
    return TelegramPromptContext.from_message(message)


def _relation_decision(
    relation: TradingMessageRelation,
) -> TradingMessageRelationDecision:
    return TradingMessageRelationDecision(
        owner_id=OwnerId.OWNER_A_SHU_QIN,
        channel_id="owner_a_channel_a",
        telegram_message_id="1037",
        relation=relation,
        confidence=0.2,
    )


def test_ambiguous_relation_is_queued_for_deferred_labelling() -> None:
    repository = InMemoryMessageLabellingRepository()
    queue = DeferredQwenLabellingQueue(
        repository,
        clock=lambda: datetime(2026, 9, 17, 12, tzinfo=timezone.utc),
    )

    record = asyncio.run(
        queue.enqueue_if_needed(
            _prompt_context(),
            _relation_decision(TradingMessageRelation.AMBIGUOUS),
        )
    )

    assert record is not None
    assert record.relation_decision.needs_human_labelling is True
    assert record.labelling_status == "pending"
    assert (
        OwnerId.OWNER_A_SHU_QIN.value,
        "owner_a_channel_a",
        "1037",
    ) in repository.records


def test_unflagged_relation_does_not_enter_labelling_queue() -> None:
    repository = InMemoryMessageLabellingRepository()
    queue = DeferredQwenLabellingQueue(repository)

    record = asyncio.run(
        queue.enqueue_if_needed(
            _prompt_context(),
            _relation_decision(TradingMessageRelation.CONTINUATION),
        )
    )

    assert record is None
    assert repository.records == {}


def test_dynamodb_labelling_item_is_queryable_by_owner_channel_and_message() -> None:
    class FakeTable:
        def __init__(self) -> None:
            self.items: list[dict] = []

        def put_item(self, *, Item: dict) -> dict:
            self.items.append(Item)
            return {}

    table = FakeTable()
    queue = DeferredQwenLabellingQueue(
        DynamoDBMessageLabellingRepository(table),
        clock=lambda: datetime(2026, 9, 17, 12, tzinfo=timezone.utc),
    )

    asyncio.run(
        queue.enqueue_if_needed(
            _prompt_context(),
            _relation_decision(TradingMessageRelation.AMBIGUOUS),
        )
    )

    assert table.items[0]["owner_channel_id"] == "owner_a_shu_qin#owner_a_channel_a"
    assert table.items[0]["telegram_message_id"] == "1037"
    assert table.items[0]["labelling_status"] == "pending"
    assert table.items[0]["payload"]["relation_decision"]["confidence"] == Decimal(
        "0.2"
    )
