"""Draft AWS Secrets Manager key names and retrieval boundary."""

from __future__ import annotations

from enum import StrEnum


class SecretName(StrEnum):
    BITGET_API_CREDENTIALS = "agentic-perp-trading-bot/bitget/api-credentials"
    BITMART_API_CREDENTIALS = "agentic-perp-trading-bot/bitmart/api-credentials"
    TELEGRAM_API_CREDENTIALS = "agentic-perp-trading-bot/telegram/api-credentials"
    TELEGRAM_USER_SESSION = "agentic-perp-trading-bot/telegram/user-session"
    MCP_AUTH_TOKEN = "agentic-perp-trading-bot/mcp/auth-token"
    KILL_SWITCH_CONFIG = "agentic-perp-trading-bot/confidence/kill-switch-config"


def get_secret_payload(secret_name: SecretName) -> dict:
    """Retrieve and JSON-decode a secret in the real AWS implementation."""
    raise NotImplementedError(f"Secrets Manager retrieval not implemented: {secret_name}")
