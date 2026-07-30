"""Pure Aster Futures v1 HMAC-SHA256 request-signing boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha256
import hmac
from typing import Self
from urllib.parse import urlencode

AsterParameter = str | int | bool | Decimal


@dataclass(frozen=True, slots=True)
class AsterV1Credentials:
    """Aster API credentials loaded only inside the Lambda execution boundary."""

    api_key: str = field(repr=False)
    secret_key: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.api_key.strip() or not self.secret_key.strip():
            raise ValueError("Aster api_key and secret_key must be non-empty")

    @classmethod
    def from_secret_payload(cls, payload: Mapping[str, object]) -> Self:
        api_key = payload.get("api_key")
        secret_key = payload.get("secret_key")
        if not isinstance(api_key, str) or not isinstance(secret_key, str):
            raise ValueError("Aster secret payload requires string api_key and secret_key")
        return cls(api_key=api_key, secret_key=secret_key)


@dataclass(frozen=True, slots=True)
class AsterV1Signature:
    """Canonical query and matching signature, without any credential material."""

    query_string: str
    signature: str

    @property
    def signed_query_string(self) -> str:
        return f"{self.query_string}&signature={self.signature}"


def _serialize_parameter(value: AsterParameter) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def sign_aster_v1_parameters(
    parameters: Mapping[str, AsterParameter],
    *,
    credentials: AsterV1Credentials,
    timestamp_ms: int,
    recv_window_ms: int = 5000,
) -> AsterV1Signature:
    """Sign the exact deterministic query string that Lambda must transmit."""

    reserved = {"signature", "timestamp", "recvWindow"}
    conflicts = reserved.intersection(parameters)
    if conflicts:
        raise ValueError(f"Aster signing parameters contain reserved fields: {sorted(conflicts)}")
    if timestamp_ms < 0:
        raise ValueError("timestamp_ms must be non-negative")
    if not 1 <= recv_window_ms <= 60_000:
        raise ValueError("recv_window_ms must be between 1 and 60000")

    ordered_parameters = [
        (name, _serialize_parameter(value))
        for name, value in sorted(parameters.items())
    ]
    ordered_parameters.extend(
        [
            ("recvWindow", str(recv_window_ms)),
            ("timestamp", str(timestamp_ms)),
        ]
    )
    query_string = urlencode(ordered_parameters)
    signature = hmac.new(
        credentials.secret_key.encode(),
        query_string.encode(),
        sha256,
    ).hexdigest()
    return AsterV1Signature(query_string=query_string, signature=signature)


def aster_v1_auth_headers(credentials: AsterV1Credentials) -> dict[str, str]:
    """Build the v1 API-key header immediately before HTTPS submission."""

    return {"X-MBX-APIKEY": credentials.api_key}
