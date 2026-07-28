"""Deterministic execution limits separated from confidence inference."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from agentic_perp_trading_bot.schemas import (
    AssetGroup,
    ClosedTradeOutcome,
    DeterministicRiskDecision,
    ExchangeId,
    PairBlacklistDecision,
    PairRiskLimit,
    PositionSizingDecision,
)

BTC_MAXIMUM_INSTANT_PRICE_DEVIATION = Decimal("0.00125")
MAJOR_AND_TRADFI_MAXIMUM_INSTANT_PRICE_DEVIATION = Decimal("0.0025")
GENERIC_ALT_MAXIMUM_INSTANT_PRICE_DEVIATION = Decimal("0.005")

_MAJOR_BASE_ASSETS = frozenset({"BNB", "ETH", "SOL"})
_KNOWN_QUOTE_ASSETS = ("USDT", "USDC", "BUSD", "USD")


def evaluate_deterministic_risk(
    sizing: PositionSizingDecision,
    *,
    exchange_id: ExchangeId,
    symbol: str,
    limits: PairRiskLimit,
    existing_position_notional_usdt: Decimal = Decimal("0"),
    pair_blacklisted: bool = False,
    instant_order: bool = False,
    reference_price: Decimal | None = None,
    current_price: Decimal | None = None,
    asset_group: AssetGroup | None = None,
    tradfi_perpetual_pair: bool = False,
) -> DeterministicRiskDecision:
    """Apply only reproducible execution constraints to one exchange request."""
    _validate_limit_identity(sizing, exchange_id, symbol, limits)
    if existing_position_notional_usdt < 0:
        raise ValueError("existing_position_notional_usdt must not be negative")

    cumulative_notional = (
        existing_position_notional_usdt + sizing.final_position_notional_usdt
    )
    reasons: list[str] = []
    deviation: Decimal | None = None
    maximum_deviation: Decimal | None = None

    if pair_blacklisted:
        reasons.append("trading_pair_blacklisted")
    if sizing.leverage > limits.maximum_leverage:
        reasons.append("requested_leverage_exceeds_pair_limit")
    if cumulative_notional > limits.maximum_cumulative_position_notional_usdt:
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
        symbol=symbol.upper(),
        requested_position_notional_usdt=sizing.final_position_notional_usdt,
        existing_position_notional_usdt=existing_position_notional_usdt,
        cumulative_position_notional_usdt=cumulative_notional,
        requested_leverage=sizing.leverage,
        limits=limits,
        reasons=reasons,
        instant_price_deviation=deviation,
        maximum_instant_price_deviation=maximum_deviation,
    )


def instant_price_deviation_threshold(
    *,
    symbol: str | None,
    asset_group: AssetGroup | None,
    tradfi_perpetual_pair: bool = False,
) -> Decimal:
    if tradfi_perpetual_pair or asset_group == AssetGroup.TRADFI:
        return MAJOR_AND_TRADFI_MAXIMUM_INSTANT_PRICE_DEVIATION

    base_asset = _base_asset(symbol)
    if base_asset == "BTC":
        return BTC_MAXIMUM_INSTANT_PRICE_DEVIATION
    if base_asset in _MAJOR_BASE_ASSETS:
        return MAJOR_AND_TRADFI_MAXIMUM_INSTANT_PRICE_DEVIATION
    return GENERIC_ALT_MAXIMUM_INSTANT_PRICE_DEVIATION


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
            and outcome.symbol.upper() == symbol.upper()
            and cutoff <= outcome.closed_at <= evaluated_at
            and outcome.net_pnl_usdt != 0
        ]
        wins = sum(outcome.net_pnl_usdt > 0 for outcome in matching)
        losses = sum(outcome.net_pnl_usdt < 0 for outcome in matching)
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
    symbol: str,
    limits: PairRiskLimit,
) -> None:
    if limits.owner_id != sizing.owner_id:
        raise ValueError("risk limit owner does not match sizing owner")
    if limits.exchange_id != exchange_id:
        raise ValueError("risk limit exchange does not match request exchange")
    if limits.symbol.upper() != symbol.upper():
        raise ValueError("risk limit symbol does not match request symbol")


def _base_asset(symbol: str | None) -> str | None:
    if symbol is None:
        return None
    normalized = "".join(character for character in symbol.upper() if character.isalnum())
    for quote_asset in _KNOWN_QUOTE_ASSETS:
        if normalized.endswith(quote_asset) and len(normalized) > len(quote_asset):
            return normalized[: -len(quote_asset)]
    return normalized or None
