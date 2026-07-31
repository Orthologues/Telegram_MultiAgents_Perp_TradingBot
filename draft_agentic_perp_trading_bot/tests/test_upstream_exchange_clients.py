from decimal import Decimal
from types import SimpleNamespace

import pytest

from agentic_perp_trading_bot.aws_execution import (
    AsterV3Credentials,
    create_aster_v3_client,
)
from agentic_perp_trading_bot.aws_execution import upstream_clients
from agentic_perp_trading_bot.aws_execution.secrets import (
    SecretName,
    exchange_signing_secret,
)
from agentic_perp_trading_bot.mcp_gateway.upstream_contracts import (
    ASTER_V3_TARGET,
    HYPERLIQUID_MCP_TARGET,
    aster_v3_order_invocation,
    hyperliquid_mcp_order_invocation,
)
from agentic_perp_trading_bot.schemas import ExchangeId


def test_aster_v3_client_delegates_to_official_upstream(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeAsterClientV3:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(
        upstream_clients,
        "import_module",
        lambda name: SimpleNamespace(AsterClientV3=FakeAsterClientV3),
    )
    credentials = AsterV3Credentials(
        user=f"0x{'1' * 40}",
        signer=f"0x{'2' * 40}",
        private_key=f"0x{'3' * 64}",
    )

    client = create_aster_v3_client(
        credentials,
        base_url="https://fapi.asterdex-testnet.com",
    )

    assert isinstance(client, FakeAsterClientV3)
    assert captured == {
        "user": credentials.user,
        "signer": credentials.signer,
        "private_key": credentials.private_key,
        "base_url": "https://fapi.asterdex-testnet.com",
    }
    assert credentials.private_key not in repr(credentials)


def test_aster_v3_credentials_validate_wallet_material() -> None:
    with pytest.raises(ValueError, match="40 hexadecimal digits"):
        AsterV3Credentials(
            user="0x1",
            signer=f"0x{'2' * 40}",
            private_key=f"0x{'3' * 64}",
        )


def test_exchange_proxy_targets_are_pinned_to_reviewed_upstreams() -> None:
    assert ASTER_V3_TARGET.interface.endswith("AsterClientV3")
    assert ASTER_V3_TARGET.operation == "create_order"
    assert len(ASTER_V3_TARGET.revision) == 40
    assert HYPERLIQUID_MCP_TARGET.operation == "hyperliquid_place_order"
    assert len(HYPERLIQUID_MCP_TARGET.revision) == 40


def test_guarded_handoffs_emit_upstream_native_order_arguments() -> None:
    aster = aster_v3_order_invocation(
        symbol="BTCUSDT",
        side="BUY",
        order_type="LIMIT",
        quantity=Decimal("0.001"),
        price=Decimal("90000"),
        time_in_force="GTC",
        reduce_only=False,
        source_intent_id="intent-123",
    )
    hyperliquid = hyperliquid_mcp_order_invocation(
        asset_index=3,
        is_buy=True,
        size=Decimal("0.001"),
        price=None,
        time_in_force="Ioc",
        reduce_only=False,
        source_intent_id="intent-123",
    )

    assert aster["target"]["operation"] == "create_order"
    assert aster["arguments"]["quantity"] == "0.001"
    assert hyperliquid["target"]["operation"] == "hyperliquid_place_order"
    assert hyperliquid["arguments"]["asset"] == 3
    assert hyperliquid["arguments"]["price"] == "0"
    assert hyperliquid["arguments"]["orderType"] == {"limit": {"tif": "Ioc"}}
    assert aster["arguments"]["new_client_order_id"] == hyperliquid["arguments"]["cloid"]


def test_aster_uses_api_wallet_secret_boundary() -> None:
    assert exchange_signing_secret(ExchangeId.ASTER) == SecretName.ASTER_API_WALLET
    assert SecretName.ASTER_API_WALLET.value.endswith("/aster/api-wallet")
