"""Outcome and venue-comparison contracts.

File mappings:
``domain/contracts/performance.py`` <- ``frameworkless_app/schemas.py``;
``domain/contracts/definitions.py`` <- ``frameworkless_app/schemas.py``.
"""

from crewai_app.domain.contracts.definitions import (
    ClosedTradeOutcome,
    PerformanceMetricsSnapshot,
    TestnetVenuePerformanceComparison,
    VenuePerformanceSummary,
)

__all__ = [
    "ClosedTradeOutcome",
    "PerformanceMetricsSnapshot",
    "TestnetVenuePerformanceComparison",
    "VenuePerformanceSummary",
]
