"""Adapters that load Flow context through existing persistence contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from crewai_app.domain.contracts.schemas import (
    OwnerRagProfile,
    SerialRagExample,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradeThreadCursor,
)
from crewai_app.domain.lifecycle.cursor import ConcurrentTradeCursorManager
from crewai_app.adapters.telegram import ReplyTreeStore
from crewai_app.domain.policies.rag_curation import validated_serial_rag_examples


class ReplyTreeParentContextLoader:
    def __init__(self, store: ReplyTreeStore) -> None:
        self.store = store

    async def load(self, message: TelegramMessageEnvelope) -> TelegramPromptContext:
        return await self.store.prompt_context_for(message)


class TradeCursorContextLoader:
    def __init__(self, manager: ConcurrentTradeCursorManager) -> None:
        self.manager = manager

    async def load(self, message: TelegramMessageEnvelope) -> List[TradeThreadCursor]:
        return await self.manager.resolve_for_message(message)


class LocalOwnerProfileRagLoader:
    """Local development adapter; production retrieval belongs behind private S3."""

    def __init__(self, profiles_root: Path) -> None:
        self.profiles_root = profiles_root

    async def load(self, message: TelegramMessageEnvelope) -> List[SerialRagExample]:
        profile_path = (
            self.profiles_root / message.owner_id.value / "shared_style.json"
        )
        profile = OwnerRagProfile.model_validate(
            json.loads(profile_path.read_text(encoding="utf-8"))
        )
        if profile.owner_id != message.owner_id:
            raise ValueError("owner RAG profile does not match the requested owner")
        return validated_serial_rag_examples(profile.serial_rag_examples)
