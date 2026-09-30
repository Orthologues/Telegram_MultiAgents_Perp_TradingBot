"""Explicit tool-type allowlists for the canonical CrewAI agents."""

from __future__ import annotations

from crewai.tools import BaseTool

from crewai_app.tools.cursor_context_tool import CursorContextTool
from crewai_app.tools.market_snapshot_tool import MarketSnapshotTool
from crewai_app.tools.parent_context_tool import ParentContextTool
from crewai_app.tools.serial_rag_tool import SerialRagTool

QWEN_AGENT_ALLOWED_TOOL_TYPES: frozenset[type[BaseTool]] = frozenset(
    {
        CursorContextTool,
        MarketSnapshotTool,
        ParentContextTool,
        SerialRagTool,
    }
)
# Read-only tools currently permitted for owner-specific QWEN agents.

MINISTRAL_AGENT_ALLOWED_TOOL_TYPES: frozenset[type[BaseTool]] = frozenset(
    {
        CursorContextTool,
        MarketSnapshotTool,
        ParentContextTool,
        SerialRagTool,
    }
)
# Read-only tools currently permitted for the shared Ministral agent.
