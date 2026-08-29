"""Pinned upstream interfaces used by the augmented exchange MCP proxies."""

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


ASTER_V3_TARGET = UpstreamProxyTarget(
    repository="https://github.com/asterdex/aster-mcp",
    revision="71fa3cf02401573f7450668c265c8f4b11c78db0",
    package="aster-mcp",
    interface="aster_mcp.v3_client.AsterClientV3",
    operation="create_order",
)

HYPERLIQUID_MCP_TARGET = UpstreamProxyTarget(
    repository="https://github.com/Dakkshin/hyperliquid-mcp",
    revision="812cbd155f0d2a714d2dbf3407d13096ce3a8c1d",
    package="mcp-hyperliquid",
    interface="hyperliquid_mcp.server.HyperliquidMCPServer",
    operation="hyperliquid_place_order",
)


def aster_v3_order_invocation(
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
        "target": ASTER_V3_TARGET.as_dict(),
        "arguments": {
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "quantity": str(quantity),
            "price": str(price) if price is not None else None,
            "time_in_force": time_in_force,
            "reduce_only": reduce_only,
            "new_client_order_id": stable_client_order_id(source_intent_id),
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
    """Return the 128-bit hex client-order form accepted by both upstreams."""
    return f"0x{sha256(source_intent_id.encode()).hexdigest()[:32]}"
