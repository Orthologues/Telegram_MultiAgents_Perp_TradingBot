"""Confidence mapping and the two allowed hard rejection checks."""

from __future__ import annotations

from decimal import Decimal

from agentic_perp_trading_bot.schemas import (
    AssetGroup,
    ConfidenceDecision,
    StrategyTier,
)

BTC_MAXIMUM_INSTANT_PRICE_DEVIATION = Decimal("0.00125")
MAJOR_AND_TRADFI_MAXIMUM_INSTANT_PRICE_DEVIATION = Decimal("0.0025")
GENERIC_ALT_MAXIMUM_INSTANT_PRICE_DEVIATION = Decimal("0.005")

_MAJOR_BASE_ASSETS = frozenset({"BNB", "ETH", "SOL"})
_KNOWN_QUOTE_ASSETS = ("USDT", "USDC", "BUSD", "USD")


def evaluate_confidence(
    source_confidence: float,
    *,
    pair_blacklisted: bool = False,
    instant_order: bool = False,
    reference_price: Decimal | None = None,
    current_price: Decimal | None = None,
    symbol: str | None = None,
    asset_group: AssetGroup | None = None,
    tradfi_perpetual_pair: bool = False,
) -> ConfidenceDecision:
    """Map confidence to a tier and apply only the two explicit hard rejections."""
    confidence = min(max(float(source_confidence), 0.0), 1.0)
    strategy_tier = _strategy_tier_for(confidence)
    reasons: list[str] = []
    instant_price_deviation: Decimal | None = None
    maximum_instant_price_deviation: Decimal | None = None

    if pair_blacklisted:
        reasons.append("trading_pair_blacklisted")

    if instant_order and reference_price is not None and current_price is not None:
        if reference_price <= 0 or current_price <= 0:
            reasons.append("invalid_instant_order_price")
        else:
            instant_price_deviation = (
                abs(current_price - reference_price) / reference_price
            )
            maximum_instant_price_deviation = instant_price_deviation_threshold(
                symbol=symbol,
                asset_group=asset_group,
                tradfi_perpetual_pair=tradfi_perpetual_pair,
            )
            if instant_price_deviation > maximum_instant_price_deviation:
                reasons.append("instant_order_price_too_far_from_reference")

    return ConfidenceDecision(
        approved=not reasons,
        confidence=confidence,
        strategy_tier=strategy_tier,
        reasons=reasons,
        instant_price_deviation=instant_price_deviation,
        maximum_instant_price_deviation=maximum_instant_price_deviation,
    )


def instant_price_deviation_threshold(
    *,
    symbol: str | None,
    asset_group: AssetGroup | None,
    tradfi_perpetual_pair: bool = False,
) -> Decimal:
    """Return the deterministic maximum deviation for an instant order."""
    if tradfi_perpetual_pair or asset_group == AssetGroup.TRADFI:
        return MAJOR_AND_TRADFI_MAXIMUM_INSTANT_PRICE_DEVIATION

    base_asset = _base_asset(symbol)
    if base_asset == "BTC":
        return BTC_MAXIMUM_INSTANT_PRICE_DEVIATION
    if base_asset in _MAJOR_BASE_ASSETS:
        return MAJOR_AND_TRADFI_MAXIMUM_INSTANT_PRICE_DEVIATION
    return GENERIC_ALT_MAXIMUM_INSTANT_PRICE_DEVIATION


def _base_asset(symbol: str | None) -> str | None:
    if symbol is None:
        return None
    normalized = "".join(character for character in symbol.upper() if character.isalnum())
    for quote_asset in _KNOWN_QUOTE_ASSETS:
        if normalized.endswith(quote_asset) and len(normalized) > len(quote_asset):
            return normalized[: -len(quote_asset)]
    return normalized or None


def _strategy_tier_for(confidence: float) -> StrategyTier:
    if confidence < 0.5:
        return StrategyTier.CONSERVATIVE
    if confidence < 0.8:
        return StrategyTier.INTERMEDIATE
    return StrategyTier.RADICAL
