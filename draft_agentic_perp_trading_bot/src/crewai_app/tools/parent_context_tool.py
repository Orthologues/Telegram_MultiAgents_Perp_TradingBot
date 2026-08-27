"""Read-only chronological parent-context tool."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from crewai_app.domain.contracts.schemas import (
    TelegramMessageEnvelope,
    TelegramPromptContext,
)
from crewai_app.tools._base import TradingBotTool


class ParentContextInput(BaseModel):
    message: TelegramMessageEnvelope


class ParentContextTool(TradingBotTool):
    name: str = "load_parent_messages"
    description: str = "Load ID-labelled Telegram parent messages in chronological order."
    args_schema: type[BaseModel] = ParentContextInput
    agent_accessible: bool = True
    loader: Callable[[TelegramMessageEnvelope], TelegramPromptContext] = Field(exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, message: TelegramMessageEnvelope | dict) -> dict:
        envelope = TelegramMessageEnvelope.model_validate(message)
        context = self.loader(envelope)
        return context.model_dump(mode="json")
