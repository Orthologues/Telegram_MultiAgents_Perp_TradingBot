"""Draft exchange gateway interface.

The MCP transport should be Streamable HTTP at `/mcp`. Internally, exchange live
state can be maintained through WebSocket workers, while signed order execution
should use REST or the AWS Lambda execution boundary.
"""

from __future__ import annotations

from typing import Protocol

from agentic_perp_trading_bot.schemas import (
    ApprovedExecutionRequest,
    ExchangeTradeState,
    MarketAnalysisSnapshot,
    PositionDirection,
    TakeProfitProtectionDecision,
)


class ExchangeGateway(Protocol):
    async def get_market_analysis(self, symbol: str) -> MarketAnalysisSnapshot:
        """Return liquidity and 5m/15m/1h/4h indicator inputs for Ministral."""

    async def get_positions(self) -> dict:
        """Return account positions through a narrow exchange-specific adapter."""

    async def get_trade_state(
        self,
        symbol: str,
        direction: PositionDirection,
    ) -> ExchangeTradeState:
        """Return active order and open position IDs for one cursor identity."""

    async def submit_approved_order(self, request: ApprovedExecutionRequest) -> dict:
        """Submit an approved order request through the execution boundary."""

    async def submit_stop_loss_adjustment(
        self,
        decision: TakeProfitProtectionDecision,
    ) -> dict:
        """Apply an idempotent Ministral-approved stop adjustment."""

    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        """Cancel an order through a narrow signed endpoint."""


class BitgetGateway:
    exchange_id = "bitget"


class BitMartGateway:
    exchange_id = "bitmart"
