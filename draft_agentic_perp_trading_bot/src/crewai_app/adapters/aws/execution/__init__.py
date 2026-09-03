"""Lambda execution boundary; never exposed as an agent tool."""

from frameworkless_app.aws_execution.lambda_handler import handler

__all__ = ["handler"]
