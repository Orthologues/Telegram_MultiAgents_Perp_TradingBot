"""AWS Lambda boundary for approved order execution.

File mappings:
``adapters/aws/execution/lambda_handler.py`` <-
``frameworkless_app/aws_execution/lambda_handler.py``;
``domain/contracts/__init__.py`` <- ``frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from crewai_app.domain.contracts import (
    ApprovedExecutionRequest,
    ExchangeNetwork,
)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Execute an approved order request after loading exchange secrets.

    Real implementation responsibilities:
    - parse ApprovedExecutionRequest
    - load Aster or Hyperliquid API-wallet secrets
    - sign Aster V1 requests with the API secret inside Lambda
    - delegate Hyperliquid signing and response parsing to the upstream MCP/SDK
    - enforce kill-switch config
    - write execution audit logs
    """
    request_payload = event.get("approved_execution_request")
    if not isinstance(request_payload, dict):
        return {
            "status": "invalid_request",
            "message": "approved_execution_request is required.",
            "request_id": getattr(context, "aws_request_id", None),
        }
    try:
        request = ApprovedExecutionRequest.model_validate(request_payload)
    except ValidationError:
        return {
            "status": "invalid_request",
            "message": "approved_execution_request failed schema validation.",
            "request_id": getattr(context, "aws_request_id", None),
        }
    if request.intent.execution_network == ExchangeNetwork.MAINNET:
        return {
            "status": "mainnet_disabled",
            "message": "This scaffold permits testnet planning only.",
            "request_id": getattr(context, "aws_request_id", None),
        }
    return {
        "status": "not_implemented",
        "message": "Validated testnet request; venue request submission is not implemented.",
        "network": request.intent.execution_network.value,
        "target_exchanges": [exchange_id.value for exchange_id in request.intent.target_exchanges],
        "request_id": getattr(context, "aws_request_id", None),
    }


__all__ = ["handler"]
