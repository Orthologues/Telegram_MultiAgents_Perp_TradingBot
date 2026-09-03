"""Draft exchange gateway interface.

The MCP transport should be Streamable HTTP at `/mcp`. Internally, exchange live
state can be maintained through WebSocket workers, while signed order execution
should use REST or the AWS Lambda execution boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from frameworkless_app.mcp_gateway.venue_contracts import (
    ExchangeEndpointProfile,
    get_exchange_profile,
)
from frameworkless_app.schemas import (
    ApprovedExecutionRequest,
    ExchangeId,
    ExchangeNetwork,
    ExchangeTradeState,
    MarketAnalysisSnapshot,
    PositionDirection,
    SettlementAsset,
    TakeProfitProtectionDecision,
)


class ExchangeGateway(Protocol):
    exchange_id: ExchangeId
    network: ExchangeNetwork
    settlement_asset: SettlementAsset

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


@dataclass(frozen=True, slots=True)
class AsterGateway:
    """Aster USDT-perpetual adapter marker; testnet is the default."""

    network: ExchangeNetwork = ExchangeNetwork.TESTNET
    exchange_id: ExchangeId = ExchangeId.ASTER
    settlement_asset: SettlementAsset = SettlementAsset.USDT

    @property
    def endpoints(self) -> ExchangeEndpointProfile:
        return get_exchange_profile(self.exchange_id, self.network)


@dataclass(frozen=True, slots=True)
class HyperliquidGateway:
    """Hyperliquid USDC-perpetual adapter marker; testnet is the default."""

    network: ExchangeNetwork = ExchangeNetwork.TESTNET
    exchange_id: ExchangeId = ExchangeId.HYPERLIQUID
    settlement_asset: SettlementAsset = SettlementAsset.USDC

    @property
    def endpoints(self) -> ExchangeEndpointProfile:
        return get_exchange_profile(self.exchange_id, self.network)
