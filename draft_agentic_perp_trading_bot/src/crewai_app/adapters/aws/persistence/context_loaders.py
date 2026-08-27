"""Adapters that load Flow context through existing persistence contracts."""

from __future__ import annotations

import json
from pathlib import Path

from crewai_app.domain.contracts.schemas import (
    OwnerRagProfile,
    SerialRagExample,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradeThreadCursor,
)
from crewai_app.domain.lifecycle.cursor import ConcurrentTradeCursorManager
from crewai_app.adapters.telegram import ReplyTreeStore


class ReplyTreeParentContextLoader:
    def __init__(self, store: ReplyTreeStore) -> None:
        self.store = store

    async def load(self, message: TelegramMessageEnvelope) -> TelegramPromptContext:
        return await self.store.prompt_context_for(message)


class TradeCursorContextLoader:
    def __init__(self, manager: ConcurrentTradeCursorManager) -> None:
        self.manager = manager

    async def load(self, message: TelegramMessageEnvelope) -> list[TradeThreadCursor]:
        return await self.manager.resolve_for_message(message)


class LocalOwnerProfileRagLoader:
    """Local development adapter; production retrieval belongs behind private S3."""

    def __init__(self, profiles_root: Path) -> None:
        self.profiles_root = profiles_root

    async def load(self, message: TelegramMessageEnvelope) -> list[SerialRagExample]:
        profile_path = (
            self.profiles_root / message.owner_id.value / "shared_style.json"
        )
        profile = OwnerRagProfile.model_validate(
            json.loads(profile_path.read_text(encoding="utf-8"))
        )
        return list(profile.serial_rag_examples)
