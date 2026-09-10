"""Lambda execution boundary; never exposed as an agent tool.

File mappings:
``adapters/aws/execution/__init__.py`` <- ``frameworkless_app/aws_execution/__init__.py``;
``adapters/aws/execution/{lambda_handler,secrets,upstream_clients}.py``
<- ``frameworkless_app/aws_execution/{lambda_handler,secrets,upstream_clients}.py``.
"""

from crewai_app.adapters.aws.execution.lambda_handler import handler
from crewai_app.adapters.aws.execution.upstream_clients import (
    AsterV1Client,
    AsterV1Credentials,
    AsterV1RestClient,
    create_aster_v1_client,
    sign_aster_v1_params,
)

__all__ = [
    "AsterV1Client",
    "AsterV1Credentials",
    "AsterV1RestClient",
    "create_aster_v1_client",
    "handler",
    "sign_aster_v1_params",
]
