import asyncio
from decimal import Decimal

import pytest
from pydantic import ValidationError

from agentic_perp_trading_bot.schemas import ExchangeNetwork
from mcp_servers.aster_mcp.server import AsterConfig, AsterPublicClient
from mcp_servers.hyperliquid_mcp.server import (
    HyperliquidConfig,
    HyperliquidInfoClient,
    HyperliquidOrderIntent,
)


def test_mainnet_handoffs_require_an_independent_opt_in() -> None:
    for config in (
        AsterConfig(
            network=ExchangeNetwork.MAINNET,
            enable_execution_handoff=True,
        ),
        HyperliquidConfig(
            network=ExchangeNetwork.MAINNET,
            enable_execution_handoff=True,
        ),
    ):
        with pytest.raises(PermissionError, match="Mainnet handoff is disabled"):
            config.require_execution_handoff()


def test_aster_symbol_resolution_uses_exchange_info() -> None:
    client = AsterPublicClient(AsterConfig())
    client._exchange_info = {
        "symbols": [
            {"symbol": "BTCUSDT", "status": "TRADING"},
            {"symbol": "OLDUSDT", "status": "BREAK"},
        ]
    }
    client._exchange_info_expires_at = float("inf")

    resolved = asyncio.run(client.require_tradable_symbol("btcusdt"))
    assert resolved["symbol"] == "BTCUSDT"
    with pytest.raises(PermissionError, match="is not trading"):
        asyncio.run(client.require_tradable_symbol("OLDUSDT"))
    with pytest.raises(PermissionError, match="does not exist"):
        asyncio.run(client.require_tradable_symbol("MISSINGUSDT"))


def test_hyperliquid_asset_indexes_are_resolved_from_network_metadata() -> None:
    client = HyperliquidInfoClient(HyperliquidConfig())
    client._meta = {"universe": [{"name": "BTC"}, {"name": "ETH"}]}
    client._meta_expires_at = float("inf")

    assert asyncio.run(client.require_perpetual_asset_index("ETH")) == 1
    with pytest.raises(PermissionError, match="does not exist"):
        asyncio.run(client.require_perpetual_asset_index("MISSING"))


def test_hyperliquid_market_intents_require_bounded_ioc_submission() -> None:
    with pytest.raises(ValidationError, match="market intents require Ioc"):
        HyperliquidOrderIntent(
            intent_id="intent-123",
            coin="BTC",
            is_buy=True,
            size=Decimal("0.001"),
            leverage=2,
            order_type="market",
            reference_price=Decimal("100000"),
        )

    intent = HyperliquidOrderIntent(
        intent_id="intent-123",
        coin="BTC",
        is_buy=True,
        size=Decimal("0.001"),
        leverage=2,
        order_type="market",
        reference_price=Decimal("100000"),
        time_in_force="Ioc",
    )
    assert intent.estimated_notional_usd == Decimal("100.000")
