"""Network, settlement, endpoint, and signing contracts for exchange adapters."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_perp_trading_bot.schemas import (
    ExchangeId,
    ExchangeNetwork,
    SettlementAsset,
    settlement_asset_for_exchange,
)


@dataclass(frozen=True, slots=True)
class ExchangeEndpointProfile:
    exchange_id: ExchangeId
    network: ExchangeNetwork
    settlement_asset: SettlementAsset
    rest_url: str
    market_websocket_url: str
    user_websocket_url: str
    metadata_path: str
    order_path: str
    signing_scheme: str
    chain_id: int | None = None


_PROFILES = {
    (ExchangeId.ASTER, ExchangeNetwork.MAINNET): ExchangeEndpointProfile(
        exchange_id=ExchangeId.ASTER,
        network=ExchangeNetwork.MAINNET,
        settlement_asset=SettlementAsset.USDT,
        rest_url="https://fapi.asterdex.com",
        market_websocket_url="wss://fstream.asterdex.com",
        user_websocket_url="wss://fstream.asterdex.com",
        metadata_path="/fapi/v3/exchangeInfo",
        order_path="/fapi/v3/order",
        signing_scheme="eip712_signer",
        chain_id=1666,
    ),
    (ExchangeId.ASTER, ExchangeNetwork.TESTNET): ExchangeEndpointProfile(
        exchange_id=ExchangeId.ASTER,
        network=ExchangeNetwork.TESTNET,
        settlement_asset=SettlementAsset.USDT,
        rest_url="https://fapi.asterdex-testnet.com",
        market_websocket_url="wss://fstream5.asterdex-testnet.com",
        user_websocket_url="wss://fstream.asterdex-testnet.com",
        metadata_path="/fapi/v3/exchangeInfo",
        order_path="/fapi/v3/order",
        signing_scheme="eip712_signer",
        chain_id=714,
    ),
    (ExchangeId.HYPERLIQUID, ExchangeNetwork.MAINNET): ExchangeEndpointProfile(
        exchange_id=ExchangeId.HYPERLIQUID,
        network=ExchangeNetwork.MAINNET,
        settlement_asset=SettlementAsset.USDC,
        rest_url="https://api.hyperliquid.xyz",
        market_websocket_url="wss://api.hyperliquid.xyz/ws",
        user_websocket_url="wss://api.hyperliquid.xyz/ws",
        metadata_path="/info",
        order_path="/exchange",
        signing_scheme="approved_api_wallet",
    ),
    (ExchangeId.HYPERLIQUID, ExchangeNetwork.TESTNET): ExchangeEndpointProfile(
        exchange_id=ExchangeId.HYPERLIQUID,
        network=ExchangeNetwork.TESTNET,
        settlement_asset=SettlementAsset.USDC,
        rest_url="https://api.hyperliquid-testnet.xyz",
        market_websocket_url="wss://api.hyperliquid-testnet.xyz/ws",
        user_websocket_url="wss://api.hyperliquid-testnet.xyz/ws",
        metadata_path="/info",
        order_path="/exchange",
        signing_scheme="approved_api_wallet",
    ),
}


def get_exchange_profile(
    exchange_id: ExchangeId,
    network: ExchangeNetwork = ExchangeNetwork.TESTNET,
) -> ExchangeEndpointProfile:
    profile = _PROFILES[(exchange_id, network)]
    expected_settlement = settlement_asset_for_exchange(exchange_id)
    if profile.settlement_asset != expected_settlement:
        raise RuntimeError("exchange endpoint profile has inconsistent settlement")
    return profile
