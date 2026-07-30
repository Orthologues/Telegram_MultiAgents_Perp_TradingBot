import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from agentic_perp_trading_bot.orchestrator import process_message
from agentic_perp_trading_bot.schemas import (
    AssetGroup,
    CanonicalTradeIntent,
    ExchangeId,
    FilterDecision,
    IntentType,
    LifecycleStrategySource,
    OwnerId,
    QwenSignalHypothesis,
    QwenStrategyCandidateSet,
    StrategyTier,
    TelegramMessageEnvelope,
    TradeAction,
)


def test_orchestrator_reviews_five_tiers_and_selects_one_for_both_exchanges() -> None:
    message = TelegramMessageEnvelope(
        owner_id=OwnerId.OWNER_A_SHU_QIN,
        channel_id="owner_a_channel_a",
        asset_group=AssetGroup.MIXED,
        telegram_message_id="123",
        received_at=datetime.now(timezone.utc),
        dedup_key="message-123",
    )
    candidates = {
        tier: QwenSignalHypothesis(
            owner_id=message.owner_id,
            channel_id=message.channel_id,
            asset_group=message.asset_group,
            model_id="qwen-test",
            strategy_tier=tier,
            intent_type=IntentType.NEW_ORDER,
            symbol="BTCUSDT",
            direction="long",
            entries=[Decimal(index + 1)],
            stop_loss=Decimal("0.9"),
            confidence=0.9,
        )
        for index, tier in enumerate(StrategyTier)
    }
    reviewed_tiers: list[StrategyTier] = []

    class QwenStub:
        async def infer_strategy_candidates(self, message, prompt_context=None):
            return QwenStrategyCandidateSet(
                owner_id=message.owner_id,
                channel_id=message.channel_id,
                asset_group=message.asset_group,
                model_id="qwen-test",
                interpretation_confidence=0.9,
                candidates=candidates,
                source_dedup_key=message.dedup_key,
            )

    class MinistralStub:
        async def review(self, hypothesis, prompt_context, market_snapshot=None):
            reviewed_tiers.append(hypothesis.strategy_tier)
            return FilterDecision(
                status="approved",
                quality_score=0.9,
                canonical_intent=CanonicalTradeIntent(
                    owner_id=hypothesis.owner_id,
                    channel_id=hypothesis.channel_id,
                    asset_group=hypothesis.asset_group,
                    strategy_tier=hypothesis.strategy_tier,
                    symbol="BTCUSDT",
                    action=TradeAction.OPEN_LONG,
                    order_type="limit",
                    entries=hypothesis.entries,
                    stop_loss=hypothesis.stop_loss,
                    target_exchanges=[
                        ExchangeId.HYPERLIQUID,
                        ExchangeId.ASTER,
                    ],
                ),
                reviewer_model="ministral-test",
            )

    request = asyncio.run(
        process_message(
            message,
            QwenStub(),
            MinistralStub(),
        )
    )

    assert request is not None
    assert reviewed_tiers == list(StrategyTier)
    assert request.intent.strategy_tier == StrategyTier.ULTRA_RADICAL
    assert request.intent.entries == [Decimal("5")]
    assert (
        request.lifecycle_strategy.source
        == LifecycleStrategySource.INITIAL_CONFIDENCE
    )
    assert request.lifecycle_strategy.strategy_tier == StrategyTier.ULTRA_RADICAL
    assert request.lifecycle_strategy.position_notional_usd == (
        request.sizing.final_position_notional_usd
    )
    assert request.lifecycle_strategy.leverage == request.sizing.leverage
    assert request.lifecycle_strategy.source_telegram_message_id == "123"
    assert request.lifecycle_strategy.revision == 0
    assert {
        decision.exchange_id for decision in request.risk_decisions
    } == {ExchangeId.HYPERLIQUID, ExchangeId.ASTER}
