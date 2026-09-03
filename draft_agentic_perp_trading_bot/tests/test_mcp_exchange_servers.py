import asyncio
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

from frameworkless_app.schemas import ExchangeNetwork


def _load_server_module(module_name: str, relative_path: str):
    module_path = Path(__file__).parents[1] / relative_path
    spec = spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load MCP server module: {module_path}")
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


aster_server = _load_server_module(
    "aster_mcp_server",
    "mcp_servers/aster_mcp/server.py",
)
hyperliquid_server = _load_server_module(
    "hyperliquid_mcp_server",
    "mcp_servers/hyperliquid_mcp/server.py",
)
AsterConfig = aster_server.AsterConfig
AsterV3PublicClient = aster_server.AsterV3PublicClient
HyperliquidConfig = hyperliquid_server.HyperliquidConfig
HyperliquidInfoClient = hyperliquid_server.HyperliquidInfoClient
HyperliquidOrderIntent = hyperliquid_server.HyperliquidOrderIntent


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
    client = AsterV3PublicClient(AsterConfig())
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


def test_aster_mcp_uses_v3_upstream_eip712_contract() -> None:
    endpoints = AsterConfig().endpoints

    assert endpoints.metadata_path == "/fapi/v3/exchangeInfo"
    assert endpoints.order_path == "/fapi/v3/order"
    assert endpoints.signing_scheme == "eip712_api_wallet_via_aster_mcp"
    assert endpoints.api_key_header is None


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
