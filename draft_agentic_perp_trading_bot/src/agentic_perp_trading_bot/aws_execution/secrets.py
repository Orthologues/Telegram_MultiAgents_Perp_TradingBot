"""Draft AWS Secrets Manager key names and retrieval boundary."""

from __future__ import annotations

from enum import StrEnum

from agentic_perp_trading_bot.schemas import ExchangeId


class SecretName(StrEnum):
    ASTER_API_CREDENTIALS = "agentic-perp-trading-bot/aster/api-credentials"
    HYPERLIQUID_API_WALLET = "agentic-perp-trading-bot/hyperliquid/api-wallet"
    TELEGRAM_API_CREDENTIALS = "agentic-perp-trading-bot/telegram/api-credentials"
    TELEGRAM_USER_SESSION = "agentic-perp-trading-bot/telegram/user-session"
    MCP_AUTH_TOKEN = "agentic-perp-trading-bot/mcp/auth-token"
    KILL_SWITCH_CONFIG = "agentic-perp-trading-bot/risk/kill-switch-config"


def get_secret_payload(secret_name: SecretName) -> dict:
    """Retrieve and JSON-decode a secret in the real AWS implementation."""
    raise NotImplementedError(f"Secrets Manager retrieval not implemented: {secret_name}")


def exchange_signing_secret(exchange_id: ExchangeId) -> SecretName:
    if exchange_id == ExchangeId.ASTER:
        return SecretName.ASTER_API_CREDENTIALS
    return SecretName.HYPERLIQUID_API_WALLET
