import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

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
from crewai_app.flows.telegram_signal_flow import TelegramSignalFlow


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


def test_signal_flow_wires_flagged_relation_to_labelling_queue() -> None:
    context = _prompt_context()
    message = context.current_message
    decision = _relation_decision(TradingMessageRelation.AMBIGUOUS)
    repository = InMemoryMessageLabellingRepository()

    class RelationEvaluator:
        async def classify_message_relation(
            self,
            incoming,
            prompt_context,
            serial_rag_examples,
        ):
            assert incoming == message
            assert prompt_context == context
            assert serial_rag_examples == []
            return decision

    flow = TelegramSignalFlow(
        parent_context_loader=object(),
        cursor_context_loader=object(),
        serial_rag_loader=object(),
        signal_evaluator=object(),
        market_snapshot_loader=object(),
        deterministic_decision_service=object(),
        decision_repository=object(),
        relation_evaluator=RelationEvaluator(),
        labelling_queue=DeferredQwenLabellingQueue(repository),
    )
    flow.state.message = message
    flow.state.prompt_context = context

    result = asyncio.run(flow.classify_message_relation())

    assert result == decision
    assert flow.state.relation_decision == decision
    assert flow.state.labelling_record is not None
    assert flow.state.trace_steps == ["message_relation", "deferred_labelling"]
    assert len(repository.records) == 1


def test_dynamodb_labelling_item_is_queryable_by_owner_channel_and_message() -> None:
    class FakeTable:
        def __init__(self) -> None:
            self.items: List[dict] = []

        def put_item(self, *, Item: dict, **kwargs: object) -> dict:
            self.items.append(Item)
            self.put_kwargs = kwargs
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
    assert table.put_kwargs["ConditionExpression"] == (
        "attribute_not_exists(owner_channel_id) "
        "AND attribute_not_exists(telegram_message_id)"
    )
    assert table.items[0]["payload"]["relation_decision"]["confidence"] == Decimal(
        "0.2"
    )
