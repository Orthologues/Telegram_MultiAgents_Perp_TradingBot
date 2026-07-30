from decimal import Decimal
from hashlib import sha256
import hmac

import pytest

from agentic_perp_trading_bot.aws_execution import (
    AsterV1Credentials,
    aster_v1_auth_headers,
    sign_aster_v1_parameters,
)
from agentic_perp_trading_bot.aws_execution.secrets import (
    SecretName,
    exchange_signing_secret,
)
from agentic_perp_trading_bot.schemas import ExchangeId


def test_aster_v1_signature_matches_transmitted_query_string() -> None:
    credentials = AsterV1Credentials(api_key="test-api-key", secret_key="test-secret")

    signed = sign_aster_v1_parameters(
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": Decimal("0.0010"),
            "price": Decimal("90000.00"),
            "reduceOnly": False,
        },
        credentials=credentials,
        timestamp_ms=1_721_800_000_000,
    )

    expected_signature = hmac.new(
        b"test-secret",
        signed.query_string.encode(),
        sha256,
    ).hexdigest()
    assert signed.signature == expected_signature
    assert signed.signed_query_string.endswith(f"signature={expected_signature}")
    assert "quantity=0.0010" in signed.query_string
    assert "reduceOnly=false" in signed.query_string
    assert aster_v1_auth_headers(credentials) == {"X-MBX-APIKEY": "test-api-key"}
    assert "test-secret" not in repr(credentials)


def test_aster_v1_signing_rejects_conflicting_authentication_fields() -> None:
    credentials = AsterV1Credentials(api_key="test-api-key", secret_key="test-secret")

    with pytest.raises(ValueError, match="reserved fields"):
        sign_aster_v1_parameters(
            {"symbol": "BTCUSDT", "timestamp": 1},
            credentials=credentials,
            timestamp_ms=2,
        )


def test_aster_uses_api_credentials_secret_boundary() -> None:
    assert exchange_signing_secret(ExchangeId.ASTER) == SecretName.ASTER_API_CREDENTIALS
    assert SecretName.ASTER_API_CREDENTIALS.value.endswith("/aster/api-credentials")
