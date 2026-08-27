"""Lambda execution boundary; never exposed as an agent tool."""

from agentic_perp_trading_bot.aws_execution.lambda_handler import handler

__all__ = ["handler"]
