"""Deterministic execution gates owned by the CrewAI application.

File mappings:
``domain/policies/execution_gate.py`` <- ``frameworkless_app/risk_engine/policy.py``;
``domain/contracts/__init__.py`` <- ``frameworkless_app/schemas.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from pydantic import BaseModel

from crewai_app.domain.contracts import (
    AssetGroup,
    ClosedTradeOutcome,
    DeterministicRiskDecision,
    ExchangeId,
    ExchangeNetwork,
    PairBlacklistDecision,
    PairRiskLimit,
    PositionSizingDecision,
)

BTC_MAXIMUM_INSTANT_PRICE_DEVIATION = Decimal("0.001")
ETH_MAXIMUM_INSTANT_PRICE_DEVIATION = Decimal("0.002")
GENERIC_ALT_MAXIMUM_INSTANT_PRICE_DEVIATION = Decimal("0.005")

_KNOWN_QUOTE_ASSETS = ("USDT", "USDC", "USD1")
_SUPPORTED_SYMBOL_PREFIXES = ("1000", "1M", "1K")


def evaluate_deterministic_risk(
    sizing: PositionSizingDecision,
    *,
    exchange_id: ExchangeId,
    symbol: str,
    limits: PairRiskLimit | BaseModel | Mapping[str, object],
    # TODO: Switch the default `network` to `ExchangeNetwork.MAINNET` after
    # testing and deployment are complete.
    network: ExchangeNetwork = ExchangeNetwork.TESTNET,
    existing_position_notional_usd: Decimal = Decimal("0"),
    pair_blacklisted: bool = False,
    instant_order: bool = False,
    reference_price: Decimal | None = None,
    current_price: Decimal | None = None,
    asset_group: AssetGroup | None = None,
    tradfi_perpetual_pair: bool = False,
) -> DeterministicRiskDecision:
    """Apply reproducible execution constraints to one exchange request."""
    canonical_limits = coerce_pair_risk_limit(limits)
    _validate_limit_identity(sizing, exchange_id, network, symbol, canonical_limits)
    if existing_position_notional_usd < 0:
        raise ValueError("existing_position_notional_usd must not be negative")

    cumulative_notional = (
        existing_position_notional_usd + sizing.final_position_notional_usd
    )
    reasons: list[str] = []
    deviation: Decimal | None = None
    maximum_deviation: Decimal | None = None

    if pair_blacklisted:
        reasons.append("trading_pair_blacklisted")
    if sizing.leverage > canonical_limits.maximum_leverage:
        reasons.append("requested_leverage_exceeds_pair_limit")
    if cumulative_notional > canonical_limits.maximum_cumulative_position_notional_usd:
        reasons.append("cumulative_position_notional_exceeds_pair_limit")

    if instant_order:
        if reference_price is None or current_price is None:
            reasons.append("instant_order_price_reference_unavailable")
        elif reference_price <= 0 or current_price <= 0:
            reasons.append("invalid_instant_order_price")
        else:
            deviation = abs(current_price - reference_price) / reference_price
            maximum_deviation = instant_price_deviation_threshold(
                symbol=symbol,
                asset_group=asset_group,
                tradfi_perpetual_pair=tradfi_perpetual_pair,
            )
            if deviation > maximum_deviation:
                reasons.append("instant_order_price_too_far_from_reference")

    return DeterministicRiskDecision(
        approved=not reasons,
        owner_id=sizing.owner_id,
        exchange_id=exchange_id,
        network=network,
        symbol=symbol.upper(),
        requested_position_notional_usd=sizing.final_position_notional_usd,
        existing_position_notional_usd=existing_position_notional_usd,
        cumulative_position_notional_usd=cumulative_notional,
        requested_leverage=sizing.leverage,
        limits=canonical_limits,
        reasons=reasons,
        instant_price_deviation=deviation,
        maximum_instant_price_deviation=maximum_deviation,
    )


def coerce_pair_risk_limit(
    limits: PairRiskLimit | BaseModel | Mapping[str, object],
) -> PairRiskLimit:
    """Validate legacy risk-limit payloads at the canonical contract boundary."""
    if isinstance(limits, PairRiskLimit):
        return limits
    if isinstance(limits, BaseModel):
        return PairRiskLimit.model_validate(limits.model_dump(mode="python"))
    return PairRiskLimit.model_validate(dict(limits))


def instant_price_deviation_threshold(
    *,
    symbol: str | None,
    asset_group: AssetGroup | None,
    tradfi_perpetual_pair: bool = False,
) -> Decimal:
    base_asset = _base_asset(symbol)
    if base_asset == "BTC":
        return BTC_MAXIMUM_INSTANT_PRICE_DEVIATION
    if base_asset == "ETH":
        return ETH_MAXIMUM_INSTANT_PRICE_DEVIATION
    return GENERIC_ALT_MAXIMUM_INSTANT_PRICE_DEVIATION


def validate_market_snapshot(
    *,
    snapshot_symbol: str,
    requested_symbol: str,
    snapshot_reference_price: Decimal,
    reference_price: Decimal,
    current_price: Decimal,
) -> None:
    """Validate a market snapshot before an instant-order decision."""
    if normalize_symbol_family(snapshot_symbol) != normalize_symbol_family(
        requested_symbol
    ):
        raise ValueError("preloaded market snapshot symbol family does not match request")
    if reference_price <= 0:
        raise ValueError("reference price must be positive")
    if snapshot_reference_price != reference_price:
        raise ValueError("preloaded market reference price does not match request")
    if current_price <= 0:
        raise ValueError("current price must be positive")

    price_deviation = abs(current_price - reference_price) / reference_price
    maximum_deviation = instant_price_deviation_threshold(
        symbol=requested_symbol,
        asset_group=None,
    )
    if price_deviation > maximum_deviation:
        raise ValueError(
            "preloaded market current price is too far from reference price"
        )


class PairBlacklistPolicy:
    """Evaluate recent net outcomes and stop-loss reversals for one pair."""

    def __init__(
        self,
        *,
        window_days: int = 90,
        minimum_closed_trades: int = 10,
        minimum_losses: int = 1,
        minimum_win_loss_ratio: Decimal = Decimal("0.75"),
        maximum_stop_reversal_rate: Decimal = Decimal("0.60"),
        policy_version: str = "pair-blacklist-v2",
    ) -> None:
        if window_days < 1:
            raise ValueError("window_days must be positive")
        if minimum_closed_trades < 1 or minimum_losses < 1:
            raise ValueError("minimum observations must be positive")
        self.window_days = window_days
        self.minimum_closed_trades = minimum_closed_trades
        self.minimum_losses = minimum_losses
        self.minimum_win_loss_ratio = minimum_win_loss_ratio
        self.maximum_stop_reversal_rate = maximum_stop_reversal_rate
        self.policy_version = policy_version

    def evaluate(
        self,
        *,
        exchange_id: ExchangeId,
        # TODO: Switch the default `network` to `ExchangeNetwork.MAINNET` after
        # testing and deployment are complete.
        network: ExchangeNetwork = ExchangeNetwork.TESTNET,
        symbol: str,
        outcomes: list[ClosedTradeOutcome],
        computed_at: datetime | None = None,
    ) -> PairBlacklistDecision:
        evaluated_at = computed_at or datetime.now(timezone.utc)
        cutoff = evaluated_at - timedelta(days=self.window_days)
        matching = [
            outcome
            for outcome in outcomes
            if outcome.exchange_id == exchange_id
            and outcome.network == network
            and outcome.symbol.upper() == symbol.upper()
            and cutoff <= outcome.closed_at <= evaluated_at
            and outcome.net_pnl_quote != 0
        ]
        wins = sum(outcome.net_pnl_quote > 0 for outcome in matching)
        losses = sum(outcome.net_pnl_quote < 0 for outcome in matching)
        ratio = Decimal(wins) / Decimal(losses) if losses else None
        stopped = [outcome for outcome in matching if outcome.stopped_out]
        reversal_rate = (
            Decimal(sum(outcome.reversed_after_stop for outcome in stopped))
            / Decimal(len(stopped))
            if stopped
            else None
        )

        enough_observations = (
            len(matching) >= self.minimum_closed_trades
            and losses >= self.minimum_losses
        )
        reasons: list[str] = []
        if enough_observations and ratio is not None:
            if ratio < self.minimum_win_loss_ratio:
                reasons.append("win_loss_ratio_below_threshold")
            if (
                reversal_rate is not None
                and reversal_rate > self.maximum_stop_reversal_rate
            ):
                reasons.append("stop_reversal_rate_above_threshold")

        return PairBlacklistDecision(
            exchange_id=exchange_id,
            network=network,
            symbol=symbol.upper(),
            blacklisted=bool(reasons),
            window_days=self.window_days,
            closed_trades=len(matching),
            wins=wins,
            losses=losses,
            win_loss_ratio=ratio,
            stop_reversal_rate=reversal_rate,
            reasons=reasons,
            policy_version=self.policy_version,
            computed_at=evaluated_at,
        )


def _validate_limit_identity(
    sizing: PositionSizingDecision,
    exchange_id: ExchangeId,
    network: ExchangeNetwork,
    symbol: str,
    limits: PairRiskLimit,
) -> None:
    if limits.owner_id != sizing.owner_id:
        raise ValueError("risk limit owner does not match sizing owner")
    if limits.exchange_id != exchange_id:
        raise ValueError("risk limit exchange does not match request exchange")
    if limits.network != network:
        raise ValueError("risk limit network does not match request network")
    if limits.symbol.upper() != symbol.upper():
        raise ValueError("risk limit symbol does not match request symbol")


def _base_asset(symbol: str | None) -> str | None:
    if symbol is None:
        return None
    normalized = "".join(character for character in symbol.upper() if character.isalnum())
    for quote_asset in _KNOWN_QUOTE_ASSETS:
        if normalized.endswith(quote_asset) and len(normalized) > len(quote_asset):
            base_asset = normalized[: -len(quote_asset)]
            for prefix in _SUPPORTED_SYMBOL_PREFIXES:
                if base_asset.startswith(prefix) and len(base_asset) > len(prefix):
                    base_asset = base_asset[len(prefix) :]
                    break
            return base_asset
    return normalized or None


def normalize_symbol_family(symbol: str) -> str:
    """Normalize supported multiplier-prefixed USDT contract symbols."""
    normalized = "".join(
        character for character in symbol.upper() if character.isalnum()
    )
    if not normalized.endswith("USDT"):
        return normalized
    base = normalized[:-4]
    for prefix in _SUPPORTED_SYMBOL_PREFIXES:
        if base.startswith(prefix) and len(base) > len(prefix):
            base = base[len(prefix) :]
            break
    return base + "USDT"


__all__ = [
    "BTC_MAXIMUM_INSTANT_PRICE_DEVIATION",
    "ETH_MAXIMUM_INSTANT_PRICE_DEVIATION",
    "GENERIC_ALT_MAXIMUM_INSTANT_PRICE_DEVIATION",
    "PairBlacklistPolicy",
    "evaluate_deterministic_risk",
    "instant_price_deviation_threshold",
    "normalize_symbol_family",
    "validate_market_snapshot",
]
