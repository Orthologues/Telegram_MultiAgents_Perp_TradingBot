from pydantic import ValidationError
import pytest

from frameworkless_app.mcp_gateway import (
    AsterGateway,
    HyperliquidGateway,
    get_exchange_profile,
)
from frameworkless_app.schemas import (
    ExchangeId,
    ExchangeNetwork,
    ExchangeTradeState,
    PositionDirection,
    SettlementAsset,
)


def test_exchange_profiles_default_to_separate_testnet_settlement_contracts() -> None:
    aster = AsterGateway()
    hyperliquid = HyperliquidGateway()

    assert aster.network == ExchangeNetwork.TESTNET
    assert aster.settlement_asset == SettlementAsset.USDT
    assert "asterdex-testnet" in aster.endpoints.rest_url
    assert aster.endpoints.metadata_path == "/fapi/v3/exchangeInfo"
    assert aster.endpoints.order_path == "/fapi/v3/order"
    assert aster.endpoints.signing_scheme == "eip712_api_wallet_via_aster_mcp"
    assert aster.endpoints.api_key_header is None

    assert hyperliquid.network == ExchangeNetwork.TESTNET
    assert hyperliquid.settlement_asset == SettlementAsset.USDC
    assert "hyperliquid-testnet" in hyperliquid.endpoints.rest_url
    assert hyperliquid.endpoints.order_path == "/exchange"


def test_mainnet_and_testnet_profiles_do_not_share_endpoints() -> None:
    for exchange_id in ExchangeId:
        testnet = get_exchange_profile(exchange_id, ExchangeNetwork.TESTNET)
        mainnet = get_exchange_profile(exchange_id, ExchangeNetwork.MAINNET)
        assert testnet.rest_url != mainnet.rest_url
        assert testnet.market_websocket_url != mainnet.market_websocket_url


def test_exchange_state_rejects_wrong_settlement_asset() -> None:
    with pytest.raises(ValidationError, match="require USDC settlement"):
        ExchangeTradeState(
            exchange_id=ExchangeId.HYPERLIQUID,
            settlement_asset=SettlementAsset.USDT,
            symbol="BTC",
            direction=PositionDirection.LONG,
            observed_at="2026-07-30T12:00:00Z",
        )
