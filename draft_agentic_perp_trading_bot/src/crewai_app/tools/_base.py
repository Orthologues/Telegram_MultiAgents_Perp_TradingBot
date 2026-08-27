"""Common access marker for CrewAI tools."""

from crewai.tools import BaseTool


class TradingBotTool(BaseTool):
    """Base class distinguishing read-only agent tools from Flow-only tools."""

    agent_accessible: bool = False
