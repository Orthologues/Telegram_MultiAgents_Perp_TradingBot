"""Read-only active-cursor context tool."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from crewai_app.domain.contracts.schemas import TelegramMessageEnvelope, TradeThreadCursor
from crewai_app.tools._base import TradingBotTool


class CursorContextInput(BaseModel):
    message: TelegramMessageEnvelope


class CursorContextTool(TradingBotTool):
    name: str = "load_active_trade_cursors"
    description: str = "Load active parent-linked trade cursors without mutating them."
    args_schema: type[BaseModel] = CursorContextInput
    agent_accessible: bool = True
    loader: Callable[[TelegramMessageEnvelope], list[TradeThreadCursor]] = Field(exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, message: TelegramMessageEnvelope | dict) -> list[dict]:
        envelope = TelegramMessageEnvelope.model_validate(message)
        return [cursor.model_dump(mode="json") for cursor in self.loader(envelope)]
