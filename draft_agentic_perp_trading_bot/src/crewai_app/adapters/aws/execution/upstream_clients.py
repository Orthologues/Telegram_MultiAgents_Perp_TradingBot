"""Lazy adapters for authenticated upstream exchange clients.

File mappings:
``adapters/aws/execution/upstream_clients.py`` <-
``frameworkless_app/aws_execution/upstream_clients.py``.
"""

from __future__ import annotations

import hmac
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Protocol, Self
from urllib.parse import urlencode

import httpx


class AsterV1Client(Protocol):
    """Small signed REST subset used by the Aster V1 Lambda boundary."""

    async def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float | str,
        price: float | str | None = None,
        stop_price: float | str | None = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        new_client_order_id: str | None = None,
        recv_window: int | None = None,
    ) -> Any: ...


@dataclass(frozen=True, slots=True)
class AsterV1Credentials:
    """Aster API key material loaded only inside the Lambda boundary."""

    api_key: str
    secret_key: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.api_key.strip() or not self.secret_key.strip():
            raise ValueError("Aster API key and secret key must not be blank")

    @classmethod
    def from_secret_payload(cls, payload: Mapping[str, object]) -> Self:
        api_key = payload.get("api_key")
        secret_key = payload.get("secret_key")
        if not all(isinstance(value, str) for value in (api_key, secret_key)):
            raise ValueError(
                "Aster V1 secret payload requires string api_key and secret_key"
            )
        return cls(api_key=api_key, secret_key=secret_key)


@dataclass(slots=True)
class AsterV1RestClient(AsterV1Client):
    credentials: AsterV1Credentials
    base_url: str
    timeout_seconds: float = 15.0

    async def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float | str,
        price: float | str | None = None,
        stop_price: float | str | None = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        new_client_order_id: str | None = None,
        recv_window: int = 5000,
    ) -> Any:
        params: dict[str, object] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "timeInForce": time_in_force,
            "reduceOnly": str(reduce_only).lower(),
            "recvWindow": recv_window,
            "timestamp": int(time.time() * 1000),
        }
        if price is not None:
            params["price"] = price
        if stop_price is not None:
            params["stopPrice"] = stop_price
        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id
        signed = sign_aster_v1_params(params, self.credentials.secret_key)
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            headers={"X-MBX-APIKEY": self.credentials.api_key},
        ) as client:
            response = await client.post("/fapi/v1/order", params=signed)
            if response.status_code == 503:
                raise RuntimeError(
                    "Aster order status is unknown after HTTP 503; reconcile by "
                    "client order ID before any retry"
                )
            response.raise_for_status()
            return response.json()


def sign_aster_v1_params(
    params: Mapping[str, object],
    secret_key: str,
) -> dict[str, object]:
    """Add the HMAC-SHA256 signature required by Aster signed endpoints."""
    query = urlencode([(key, value) for key, value in params.items()])
    signature = hmac.new(
        secret_key.encode("utf-8"),
        query.encode("utf-8"),
        sha256,
    ).hexdigest()
    return {**params, "signature": signature}


def create_aster_v1_client(
    credentials: AsterV1Credentials,
    *,
    base_url: str,
) -> AsterV1Client:
    """Construct the Aster V1 REST client inside the execution boundary."""
    return AsterV1RestClient(credentials=credentials, base_url=base_url)


__all__ = [
    "AsterV1Client",
    "AsterV1Credentials",
    "AsterV1RestClient",
    "create_aster_v1_client",
    "sign_aster_v1_params",
]
