"""Lambda execution boundary; never exposed as an agent tool.

File mappings:
``adapters/aws/execution/__init__.py`` <- ``frameworkless_app/aws_execution/__init__.py``;
``adapters/aws/execution/{lambda_handler,secrets,upstream_clients}.py``
<- ``frameworkless_app/aws_execution/{lambda_handler,secrets,upstream_clients}.py``.
"""

from crewai_app.adapters.aws.execution.lambda_handler import handler

__all__ = ["handler"]
