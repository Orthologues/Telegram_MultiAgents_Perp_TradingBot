"""Lazy adapters for authenticated upstream exchange clients."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Protocol, Self


class AsterV3Client(Protocol):
    """Official Aster MCP V3 client subset used by Lambda."""

    def create_order(
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
class AsterV3Credentials:
    """Aster API-wallet material loaded only inside the Lambda boundary."""

    user: str
    signer: str
    private_key: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_hex(self.user, 40, "user")
        _require_hex(self.signer, 40, "signer")
        _require_hex(self.private_key, 64, "private_key")

    @classmethod
    def from_secret_payload(cls, payload: Mapping[str, object]) -> Self:
        user = payload.get("user")
        signer = payload.get("signer")
        private_key = payload.get("private_key")
        if not all(isinstance(value, str) for value in (user, signer, private_key)):
            raise ValueError(
                "Aster V3 secret payload requires string user, signer, and private_key"
            )
        return cls(user=user, signer=signer, private_key=private_key)


def create_aster_v3_client(
    credentials: AsterV3Credentials,
    *,
    base_url: str,
) -> AsterV3Client:
    """Instantiate the official client without reimplementing EIP-712."""
    try:
        client_type = import_module("aster_mcp.v3_client").AsterClientV3
    except (AttributeError, ImportError) as exc:
        raise RuntimeError(
            "Install the exchange-upstreams extra to use authenticated Aster V3"
        ) from exc
    return client_type(
        user=credentials.user,
        signer=credentials.signer,
        private_key=credentials.private_key,
        base_url=base_url,
    )


def _require_hex(value: str, digits: int, field_name: str) -> None:
    normalized = value.removeprefix("0x")
    if len(normalized) != digits:
        raise ValueError(f"Aster {field_name} must contain {digits} hexadecimal digits")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"Aster {field_name} must be hexadecimal") from exc
