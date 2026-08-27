"""Flow-only decision persistence tool."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from crewai_app.flows.states import DecisionRecord
from crewai_app.tools._base import TradingBotTool


class DecisionPersistenceInput(BaseModel):
    decision: DecisionRecord


class DecisionPersistenceTool(TradingBotTool):
    name: str = "persist_decision"
    description: str = "Persist one Flow decision idempotently outside agent execution."
    args_schema: type[BaseModel] = DecisionPersistenceInput
    agent_accessible: bool = False
    writer: Callable[[DecisionRecord], None] = Field(exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, decision: DecisionRecord | dict) -> dict:
        record = DecisionRecord.model_validate(decision)
        self.writer(record)
        return {"flow_id": record.flow_id, "persisted": True}
