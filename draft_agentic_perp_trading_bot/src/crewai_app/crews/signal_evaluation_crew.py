"""Runner for the primary owner-QWEN and shared-Ministral Crew."""

from __future__ import annotations

from collections.abc import Sequence
from typing import List, TypeVar  # noqa: UP035

from crewai.tasks.task_output import TaskOutput
from pydantic import BaseModel

from crewai_app.agent_interfaces.qwen import (
    QwenMessageRelationAPI,
    SignalEvaluationAPI,
)
from crewai_app.crew import CrewModelSettings, TradingSignalCrew
from crewai_app.domain.contracts.schemas import (
    MinistralStrategyReviewSet,
    QwenStrategyCandidateSet,
    SerialRagExample,
    SignalEvaluationResult,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradeThreadCursor,
    TradingMessageRelationDecision,
)

SignalEvaluator = SignalEvaluationAPI
MessageRelationEvaluator = QwenMessageRelationAPI


class CrewMessageRelationEvaluator(QwenMessageRelationAPI):
    """Invoke the selected owner-QWEN relation-classification Crew."""

    def __init__(self, settings: CrewModelSettings) -> None:
        self.settings = settings

    async def classify_message_relation(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
        serial_rag_examples: List[SerialRagExample],
    ) -> TradingMessageRelationDecision:
        selected_crew = TradingSignalCrew(message.owner_id, self.settings).relation_crew()
        output = await selected_crew.kickoff_async(
            inputs={
                "owner_id": message.owner_id.value,
                "telegram_prompt_context_json": prompt_context.model_dump_json(),
                "serial_rag_examples_json": _models_json(serial_rag_examples),
            }
        )
        if len(output.tasks_output) != 1:
            raise RuntimeError("message-relation Crew must return exactly one task output")
        decision = _parse_task_output(
            output.tasks_output[0],
            TradingMessageRelationDecision,
        )
        if (
            decision.owner_id != message.owner_id
            or decision.channel_id != message.channel_id
            or decision.telegram_message_id != message.telegram_message_id
        ):
            raise ValueError("QWEN relation decision does not match the source message")
        parent_message_ids = {
            parent.telegram_message_id for parent in prompt_context.parent_messages
        }
        if not set(decision.matched_message_ids).issubset(parent_message_ids):
            raise ValueError("QWEN relation decision references an unavailable parent message")
        return decision


class CrewSignalEvaluator(SignalEvaluationAPI):
    """Invoke exactly one owner-specific QWEN definition per message."""

    def __init__(self, settings: CrewModelSettings) -> None:
        self.settings = settings

    async def evaluate(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
        serial_rag_examples: List[SerialRagExample],
        active_trade_cursors: List[TradeThreadCursor],
    ) -> SignalEvaluationResult:
        selected_crew = TradingSignalCrew(message.owner_id, self.settings).crew()
        output = await selected_crew.kickoff_async(
            inputs={
                "owner_id": message.owner_id.value,
                "telegram_prompt_context_json": prompt_context.model_dump_json(),
                "serial_rag_examples_json": _models_json(serial_rag_examples),
                "active_trade_cursors_json": _models_json(active_trade_cursors),
            }
        )
        if len(output.tasks_output) != 2:
            raise RuntimeError("signal-evaluation Crew must return exactly two task outputs")
        candidates = _parse_task_output(
            output.tasks_output[0],
            QwenStrategyCandidateSet,
        )
        reviews = _parse_task_output(
            output.tasks_output[1],
            MinistralStrategyReviewSet,
        )
        result = SignalEvaluationResult(candidates=candidates, reviews=reviews)
        result.validate_for_message(message)
        return result


OutputModel = TypeVar("OutputModel", bound=BaseModel)


def _parse_task_output(
    output: TaskOutput,
    model_type: type[OutputModel],
) -> OutputModel:
    if isinstance(output.pydantic, model_type):
        return output.pydantic
    return model_type.model_validate_json(output.raw)


def _models_json(models: Sequence[BaseModel]) -> str:
    return "[" + ",".join(model.model_dump_json() for model in models) + "]"
