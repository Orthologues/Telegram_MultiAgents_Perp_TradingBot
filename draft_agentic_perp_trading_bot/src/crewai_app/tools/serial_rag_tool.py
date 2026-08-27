"""Read-only loader for manually curated serial-RAG profiles."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from crewai_app.domain.contracts.schemas import OwnerId, OwnerRagProfile
from crewai_app.tools._base import TradingBotTool


class SerialRagInput(BaseModel):
    owner_id: OwnerId
    limit: int = Field(default=10, ge=1, le=50)


class SerialRagTool(TradingBotTool):
    name: str = "retrieve_owner_rag_examples"
    description: str = "Load authenticated serial-RAG references for one owner."
    args_schema: type[BaseModel] = SerialRagInput
    agent_accessible: bool = True
    profiles_root: Path

    def _run(self, owner_id: OwnerId | str, limit: int = 10) -> list[dict]:
        owner = OwnerId(owner_id)
        profile_path = self.profiles_root / owner.value / "shared_style.json"
        profile = OwnerRagProfile.model_validate(
            json.loads(profile_path.read_text(encoding="utf-8"))
        )
        return [
            example.model_dump(mode="json")
            for example in profile.serial_rag_examples[:limit]
        ]
