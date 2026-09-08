"""Trading-signal, strategy, position, and cursor contracts.

File mappings:
``domain/contracts/trading.py`` <- ``frameworkless_app/schemas.py``;
``domain/contracts/definitions.py`` <- ``frameworkless_app/schemas.py``.
"""

from crewai_app.domain.contracts.definitions import (
    CanonicalTradeIntent,
    ConfidenceDecision,
    ExchangeTradeState,
    FilterDecision,
    IntentType,
    LifecycleStrategySource,
    PositionDirection,
    PositionLifecycleEvent,
    PositionLifecycleStrategy,
    PositionReductionHypothesis,
    PositionSizingDecision,
    QwenSignalHypothesis,
    QwenStrategyCandidateSet,
    StrategyTier,
    TakeProfitFillEvent,
    TakeProfitLevel,
    TakeProfitProtectionAction,
    TakeProfitProtectionDecision,
    TradeAction,
    TradeCursorStatus,
    TradeThreadCursor,
    TradingMessageSynonymDecision,
)

__all__ = [
    "CanonicalTradeIntent",
    "ConfidenceDecision",
    "ExchangeTradeState",
    "FilterDecision",
    "IntentType",
    "LifecycleStrategySource",
    "PositionDirection",
    "PositionLifecycleEvent",
    "PositionLifecycleStrategy",
    "PositionReductionHypothesis",
    "PositionSizingDecision",
    "QwenSignalHypothesis",
    "QwenStrategyCandidateSet",
    "StrategyTier",
    "TakeProfitFillEvent",
    "TakeProfitLevel",
    "TakeProfitProtectionAction",
    "TakeProfitProtectionDecision",
    "TradeAction",
    "TradeCursorStatus",
    "TradeThreadCursor",
    "TradingMessageSynonymDecision",
]
