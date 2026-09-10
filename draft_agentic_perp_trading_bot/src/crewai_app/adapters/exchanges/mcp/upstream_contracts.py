"""Pinned upstream interfaces used by the augmented exchange MCP proxies.

File mappings:
``adapters/exchanges/mcp/upstream_contracts.py`` <-
``frameworkless_app/mcp_gateway/upstream_contracts.py``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Any


@dataclass(frozen=True, slots=True)
class UpstreamProxyTarget:
    repository: str
    revision: str
    package: str
    interface: str
    operation: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


ASTER_V1_TARGET = UpstreamProxyTarget(
    repository="https://docs.asterdex.com/for-developers/aster-api/api-documentation",
    revision="v1",
    package="Aster REST API",
    interface="HMAC-SHA256 REST client",
    operation="POST /fapi/v1/order",
)

HYPERLIQUID_MCP_TARGET = UpstreamProxyTarget(
    repository="https://github.com/Dakkshin/hyperliquid-mcp",
    revision="812cbd155f0d2a714d2dbf3407d13096ce3a8c1d",
    package="mcp-hyperliquid",
    interface="hyperliquid_mcp.server.HyperliquidMCPServer",
    operation="hyperliquid_place_order",
)


def aster_v1_order_invocation(
    *,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Decimal | None,
    time_in_force: str,
    reduce_only: bool,
    source_intent_id: str,
) -> dict[str, Any]:
    return {
        "target": ASTER_V1_TARGET.as_dict(),
        "arguments": {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
            "price": str(price) if price is not None else None,
            "timeInForce": time_in_force,
            "reduceOnly": reduce_only,
            "newClientOrderId": stable_client_order_id(source_intent_id),
            "recvWindow": 5000,
            "signing": "HMAC-SHA256 inside Lambda",
        },
    }


def hyperliquid_mcp_order_invocation(
    *,
    asset_index: int,
    is_buy: bool,
    size: Decimal,
    price: Decimal | None,
    reduce_only: bool,
    time_in_force: str,
    source_intent_id: str,
) -> dict[str, Any]:
    return {
        "target": HYPERLIQUID_MCP_TARGET.as_dict(),
        "arguments": {
            "asset": asset_index,
            "isBuy": is_buy,
            "size": str(size),
            "price": str(price) if price is not None else "0",
            "reduceOnly": reduce_only,
            "orderType": {"limit": {"tif": time_in_force}},
            "cloid": stable_client_order_id(source_intent_id),
        },
    }


def stable_client_order_id(source_intent_id: str) -> str:
    """Return a stable client-order identifier for either venue."""
    return sha256(source_intent_id.encode()).hexdigest()[:32]


__all__ = [
    "ASTER_V1_TARGET",
    "HYPERLIQUID_MCP_TARGET",
    "UpstreamProxyTarget",
    "aster_v1_order_invocation",
    "hyperliquid_mcp_order_invocation",
    "stable_client_order_id",
]
