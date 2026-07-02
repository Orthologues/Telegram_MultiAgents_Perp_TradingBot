"""Draft exchange gateway interface.

The MCP transport should be Streamable HTTP at `/mcp`. Internally, exchange live
state can be maintained through WebSocket workers, while signed order execution
should use REST or the AWS Lambda execution boundary.
"""

from __future__ import annotations

from typing import Protocol

from agentic_perp_trading_bot.schemas import ApprovedExecutionRequest


class ExchangeGateway(Protocol):
    async def get_market_state(self, symbol: str) -> dict:
        """Return cached market state from WebSocket-backed workers."""

    async def get_positions(self) -> dict:
        """Return account positions through a narrow exchange-specific adapter."""

    async def submit_approved_order(self, request: ApprovedExecutionRequest) -> dict:
        """Submit an approved order request through the execution boundary."""

    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        """Cancel an order through a narrow signed endpoint."""


class BitgetGateway:
    exchange_id = "bitget"


class BitMartGateway:
    exchange_id = "bitmart"
