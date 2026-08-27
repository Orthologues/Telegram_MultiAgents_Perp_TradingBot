"""Runner for the primary owner-QWEN and shared-Ministral Crew."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar

from crewai.tasks.task_output import TaskOutput
from pydantic import BaseModel

from crewai_app.crew import CrewModelSettings, TradingSignalCrew
from crewai_app.domain.contracts.schemas import (
    QwenStrategyCandidateSet,
    SerialRagExample,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradeThreadCursor,
)
from crewai_app.flows.states import (
    MinistralStrategyReviewSet,
    SignalEvaluationResult,
)


class SignalEvaluator(Protocol):
    async def evaluate(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
        serial_rag_examples: list[SerialRagExample],
        active_trade_cursors: list[TradeThreadCursor],
    ) -> SignalEvaluationResult: ...


class CrewSignalEvaluator:
    """Invoke exactly one owner-specific QWEN definition per message."""

    def __init__(self, settings: CrewModelSettings) -> None:
        self.settings = settings

    async def evaluate(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
        serial_rag_examples: list[SerialRagExample],
        active_trade_cursors: list[TradeThreadCursor],
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
        return SignalEvaluationResult(candidates=candidates, reviews=reviews)


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
