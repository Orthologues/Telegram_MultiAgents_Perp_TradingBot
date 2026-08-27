"""Read-only MCP market and liquidity snapshot tool."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from crewai_app.domain.contracts.schemas import ExchangeId
from crewai_app.flows.states import ExecutionLiquiditySnapshot
from crewai_app.tools._base import TradingBotTool


class MarketSnapshotInput(BaseModel):
    exchange_id: ExchangeId
    symbol: str = Field(min_length=1)


class MarketSnapshotTool(TradingBotTool):
    name: str = "load_market_snapshot"
    description: str = "Load a read-only MCP market, depth, and slippage snapshot."
    args_schema: type[BaseModel] = MarketSnapshotInput
    agent_accessible: bool = True
    loader: Callable[[ExchangeId, str], ExecutionLiquiditySnapshot] = Field(exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, exchange_id: ExchangeId | str, symbol: str) -> dict:
        snapshot = self.loader(ExchangeId(exchange_id), symbol)
        return snapshot.model_dump(mode="json")
