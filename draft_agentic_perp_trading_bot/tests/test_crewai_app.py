import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from crewai import Process

from crewai_app.adapters.aws.persistence.decision_repository import (
    InMemoryDecisionRepository,
)
from crewai_app.crew import CrewModelSettings, TradingSignalCrew
from crewai_app.domain.contracts.schemas import (
    ACCEPTABLE_ALTERNATIVE_OWNER_MODEL_IDS,
    AssetGroup,
    BedrockModelId,
    CanonicalTradeIntent,
    ClosedTradeOutcome,
    ExchangeId,
    ExchangeNetwork,
    ExchangeTradeState,
    FilterDecision,
    IndicatorTimeframe,
    IntentType,
    LifecycleStrategySource,
    MarketAnalysisSnapshot,
    OwnerId,
    PositionDirection,
    PositionLifecycleStrategy,
    QwenSignalHypothesis,
    QwenStrategyCandidateSet,
    SettlementAsset,
    StrategyTier,
    TechnicalIndicatorSnapshot,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TelegramPromptMessage,
    TradeAction,
    TradeCursorStatus,
    TradingPairType,
)
from crewai_app.domain.lifecycle.cursor import (
    ConcurrentTradeCursorManager,
    InMemoryTradeCursorRepository,
)
from crewai_app.flows.performance_evaluation_flow import PerformanceEvaluationFlow
from crewai_app.flows.position_lifecycle_flow import PositionLifecycleFlow
from crewai_app.flows.states import (
    ExecutionLiquiditySnapshot,
    ExecutionMode,
    MinistralStrategyReviewSet,
    SignalEvaluationResult,
    StrategyOutcome,
)
from crewai_app.flows.telegram_signal_flow import (
    CompatibilityDeterministicDecisionService,
    TelegramSignalFlow,
)
from crewai_app.tools import ConfidencePolicyTool, ParentContextTool


NOW = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)


def _model_settings() -> CrewModelSettings:
    return CrewModelSettings(
        aws_region_name="us-east-1",
        owner_qwen_model_ids={
            owner_id: BedrockModelId.QWEN3_VL_235B_A22B for owner_id in OwnerId
        },
        ministral_model_id=BedrockModelId.MINISTRAL_3_8B_INSTRUCT,
    )


def test_model_settings_default_to_selected_bedrock_ids() -> None:
    settings = CrewModelSettings(aws_region_name="us-east-1")

    assert settings.owner_qwen_model_ids == {
        owner_id: BedrockModelId.QWEN3_VL_235B_A22B for owner_id in OwnerId
    }
    assert settings.ministral_model_id == BedrockModelId.MINISTRAL_3_8B_INSTRUCT


def test_model_settings_allow_alternate_bedrock_ids() -> None:
    settings = CrewModelSettings(
        aws_region_name="us-east-1",
        owner_qwen_model_ids={
            owner_id: BedrockModelId.DEEPSEEK_V3_2 for owner_id in OwnerId
        },
        ministral_model_id="mistral.alternate",
    )

    assert (
        settings.owner_qwen_model_ids[OwnerId.OWNER_A_SHU_QIN]
        == BedrockModelId.DEEPSEEK_V3_2
    )
    assert settings.ministral_model_id == "mistral.alternate"


def test_model_settings_reject_unapproved_owner_model_ids() -> None:
    with pytest.raises(ValueError, match="approved multimodal alternative"):
        CrewModelSettings(
            aws_region_name="us-east-1",
            owner_qwen_model_ids={owner_id: "qwen.unapproved" for owner_id in OwnerId},
        )


def test_alternative_owner_model_set_excludes_qwen_and_ministral() -> None:
    assert ACCEPTABLE_ALTERNATIVE_OWNER_MODEL_IDS == frozenset(
        {
            BedrockModelId.DEEPSEEK_V3_2,
            BedrockModelId.GLM_4_7,
            BedrockModelId.GLM_4_7_FLASH,
            BedrockModelId.GLM_5,
            BedrockModelId.LLAMA_4_MAVERICK_17B_INSTRUCT,
            BedrockModelId.LLAMA_4_SCOUT_17B_INSTRUCT,
        }
    )
    assert BedrockModelId.QWEN3_VL_235B_A22B not in (
        ACCEPTABLE_ALTERNATIVE_OWNER_MODEL_IDS
    )
    assert BedrockModelId.MINISTRAL_3_8B_INSTRUCT not in (
        ACCEPTABLE_ALTERNATIVE_OWNER_MODEL_IDS
    )


def _message() -> TelegramMessageEnvelope:
    return TelegramMessageEnvelope(
        owner_id=OwnerId.OWNER_C_BI_JIA_SUO,
        channel_id="owner_c_channel",
        asset_group=AssetGroup.BTC_ETH,
        telegram_message_id="1037",
        received_at=NOW,
        parent_messages=["811", "917", "1002"],
        raw_text="test signal",
        dedup_key="owner-c:1037",
    )


def _prompt_context(message: TelegramMessageEnvelope) -> TelegramPromptContext:
    return TelegramPromptContext.from_message(
        message,
        [
            TelegramPromptMessage(telegram_message_id="811", raw_text="parent 1"),
            TelegramPromptMessage(telegram_message_id="917", raw_text="parent 2"),
            TelegramPromptMessage(telegram_message_id="1002", raw_text="parent 3"),
        ],
    )


def _evaluation(message: TelegramMessageEnvelope) -> SignalEvaluationResult:
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
            entries=[Decimal("100")],
            stop_loss=None,
            confidence=0.9,
            evidence=["telegram:1037"],
        )
        for tier in StrategyTier
    }
    candidate_set = QwenStrategyCandidateSet(
        owner_id=message.owner_id,
        channel_id=message.channel_id,
        asset_group=message.asset_group,
        model_id="qwen-test",
        interpretation_confidence=0.9,
        candidates=candidates,
        source_dedup_key=message.dedup_key,
    )
    reviews = {
        tier: FilterDecision(
            status="approved",
            quality_score=0.9,
            canonical_intent=CanonicalTradeIntent(
                owner_id=message.owner_id,
                channel_id=message.channel_id,
                asset_group=message.asset_group,
                strategy_tier=tier,
                symbol="BTCUSDT",
                action=TradeAction.OPEN_LONG,
                order_type="market",
                entries=[Decimal("100")],
                stop_loss=None,
                target_exchanges=[ExchangeId.ASTER, ExchangeId.HYPERLIQUID],
                signal_dedup_key=message.dedup_key,
            ),
            reviewer_model="ministral-test",
        )
        for tier in StrategyTier
    }
    return SignalEvaluationResult(
        candidates=candidate_set,
        reviews=MinistralStrategyReviewSet(
            owner_id=message.owner_id,
            channel_id=message.channel_id,
            reviewer_model="ministral-test",
            reviews=reviews,
        ),
    )


def _market_snapshot(exchange_id: ExchangeId) -> ExecutionLiquiditySnapshot:
    settlement_asset = (
        SettlementAsset.USDT
        if exchange_id == ExchangeId.ASTER
        else SettlementAsset.USDC
    )
    indicators = {
        timeframe: TechnicalIndicatorSnapshot(
            ema_fast=Decimal("100"),
            ema_slow=Decimal("99"),
            macd=Decimal("1"),
            macd_signal=Decimal("0.5"),
            kdj_k=Decimal("50"),
            kdj_d=Decimal("48"),
            kdj_j=Decimal("54"),
            rsi=Decimal("55"),
            bollinger_upper=Decimal("110"),
            bollinger_middle=Decimal("100"),
            bollinger_lower=Decimal("90"),
            average_true_range=Decimal("2"),
            realized_volatility_fraction=Decimal("0.03"),
        )
        for timeframe in IndicatorTimeframe
    }
    current_price = (
        Decimal("100.05")
        if exchange_id == ExchangeId.ASTER
        else Decimal("100.08")
    )
    return ExecutionLiquiditySnapshot(
        market=MarketAnalysisSnapshot(
            exchange_id=exchange_id,
            network=ExchangeNetwork.TESTNET,
            settlement_asset=settlement_asset,
            symbol="BTCUSDT",
            trading_pair_type=TradingPairType.MAINSTREAM_COIN,
            current_price=current_price,
            market_cap_usd=Decimal("1000000000000"),
            quote_volume_24h_usd=Decimal("1000000000"),
            indicators=indicators,
            observed_at=NOW,
        ),
        reference_price=Decimal("100"),
        order_book_depth_usd=Decimal("50000"),
        minimum_order_book_depth_usd=Decimal("10000"),
        expected_slippage_fraction=Decimal("0.0005"),
        maximum_expected_slippage_fraction=Decimal("0.001"),
    )


def test_canonical_crew_selects_one_owner_qwen_and_shared_ministral() -> None:
    crew = TradingSignalCrew(
        OwnerId.OWNER_C_BI_JIA_SUO,
        _model_settings(),
    ).crew()

    assert crew.process == Process.sequential
    assert len(crew.agents) == 2
    assert "Owner C" in crew.agents[0].role
    assert "Ministral" in crew.agents[1].role
    assert all(agent.allow_delegation is False for agent in crew.agents)
    assert all(agent.tools == [] for agent in crew.agents)
    assert len(crew.tasks) == 2
    assert crew.tasks[0].output_pydantic is QwenStrategyCandidateSet
    assert crew.tasks[1].output_pydantic is MinistralStrategyReviewSet


def test_flow_only_tools_cannot_be_attached_to_agents() -> None:
    with pytest.raises(ValueError, match="Flow-only tools"):
        TradingSignalCrew(
            OwnerId.OWNER_A_SHU_QIN,
            _model_settings(),
            qwen_tools=[ConfidencePolicyTool()],
        )

    read_only_tool = ParentContextTool(loader=lambda message: _prompt_context(message))
    crew = TradingSignalCrew(
        OwnerId.OWNER_A_SHU_QIN,
        _model_settings(),
        qwen_tools=[read_only_tool],
    ).crew()
    assert [tool.name for tool in crew.agents[0].tools] == ["load_parent_messages"]


def test_telegram_signal_flow_routes_persists_and_emits_guarded_testnet_intent() -> None:
    message = _message()
    evaluation = _evaluation(message)
    repository = InMemoryDecisionRepository()
    published = []

    class ParentLoader:
        async def load(self, incoming):
            return _prompt_context(incoming)

    class CursorLoader:
        async def load(self, incoming):
            return []

    class RagLoader:
        async def load(self, incoming):
            return []

    class Evaluator:
        calls = []

        async def evaluate(self, incoming, context, examples, cursors):
            self.calls.append(incoming.owner_id)
            return evaluation

    class MarketLoader:
        async def load(self, exchange_id, symbol, reference_price):
            assert symbol == "BTCUSDT"
            assert reference_price == Decimal("100")
            return _market_snapshot(exchange_id)

    class Publisher:
        async def publish(self, request):
            published.append(request)

    evaluator = Evaluator()
    flow = TelegramSignalFlow(
        parent_context_loader=ParentLoader(),
        cursor_context_loader=CursorLoader(),
        serial_rag_loader=RagLoader(),
        signal_evaluator=evaluator,
        market_snapshot_loader=MarketLoader(),
        deterministic_decision_service=CompatibilityDeterministicDecisionService(),
        decision_repository=repository,
        execution_intent_publisher=Publisher(),
        execution_mode=ExecutionMode(testnet_enabled=True),
    )

    asyncio.run(
        flow.kickoff_async(inputs={"message": message.model_dump(mode="json")})
    )

    assert evaluator.calls == [OwnerId.OWNER_C_BI_JIA_SUO]
    assert flow.state.selected_owner_id == OwnerId.OWNER_C_BI_JIA_SUO
    assert flow.state.candidate_set is not None
    assert set(flow.state.candidate_set.candidates) == set(StrategyTier)
    assert flow.state.approved_execution_request is not None
    assert flow.state.approved_execution_request.intent.strategy_tier == (
        StrategyTier.ULTRA_RADICAL
    )
    assert flow.state.approved_execution_request.intent.stop_loss is not None
    assert flow.state.decision_persisted is True
    assert repository.records[flow.state.id] == flow.state.decision_record
    assert flow.state.execution_intent_emitted is True
    assert published == [flow.state.approved_execution_request]
    assert flow.state.trace_steps == [
        "load_parent_messages",
        "load_active_trade_cursors",
        "retrieve_owner_rag_examples",
        "owner_qwen_inference",
        "validate_structured_output",
        "ministral_review",
        "load_market_snapshot",
        "confidence_selection",
        "apply_deterministic_policies",
        "persist_decision",
        "execution_intent",
    ]


def test_telegram_signal_flow_rejects_insufficient_order_book_depth() -> None:
    message = _message()
    evaluation = _evaluation(message)
    repository = InMemoryDecisionRepository()

    class ParentLoader:
        async def load(self, incoming):
            return _prompt_context(incoming)

    class EmptyLoader:
        async def load(self, incoming):
            return []

    class Evaluator:
        async def evaluate(self, incoming, context, examples, cursors):
            return evaluation

    class MarketLoader:
        async def load(self, exchange_id, symbol, reference_price):
            snapshot = _market_snapshot(exchange_id)
            if exchange_id == ExchangeId.ASTER:
                return snapshot.model_copy(
                    update={"order_book_depth_usd": Decimal("100")}
                )
            return snapshot

    flow = TelegramSignalFlow(
        parent_context_loader=ParentLoader(),
        cursor_context_loader=EmptyLoader(),
        serial_rag_loader=EmptyLoader(),
        signal_evaluator=Evaluator(),
        market_snapshot_loader=MarketLoader(),
        deterministic_decision_service=CompatibilityDeterministicDecisionService(),
        decision_repository=repository,
        execution_mode=ExecutionMode(testnet_enabled=True),
    )

    asyncio.run(
        flow.kickoff_async(inputs={"message": message.model_dump(mode="json")})
    )

    assert flow.state.approved_execution_request is None
    assert flow.state.execution_intent_emitted is False
    assert flow.state.rejection_reasons == ["insufficient_order_book_depth"]
    assert flow.state.decision_persisted is True


def _outcome(
    exchange_id: ExchangeId,
    pnl: str,
    signal_key: str,
) -> ClosedTradeOutcome:
    return ClosedTradeOutcome(
        exchange_id=exchange_id,
        settlement_asset=(
            SettlementAsset.USDT
            if exchange_id == ExchangeId.ASTER
            else SettlementAsset.USDC
        ),
        symbol="BTCUSDT",
        signal_dedup_key=signal_key,
        entry_notional_quote=Decimal("100"),
        realized_pnl_quote=Decimal(pnl),
        closed_at=NOW,
    )


def test_performance_flow_reports_venue_intersection_and_all_five_tiers() -> None:
    aster = _outcome(ExchangeId.ASTER, "5", "shared-signal")
    hyperliquid = _outcome(ExchangeId.HYPERLIQUID, "4", "shared-signal")
    flow = PerformanceEvaluationFlow()

    asyncio.run(
        flow.kickoff_async(
            inputs={
                "closed_outcomes": [
                    aster.model_dump(mode="json"),
                    hyperliquid.model_dump(mode="json"),
                ],
                "strategy_outcomes": [
                    StrategyOutcome(
                        strategy_tier=StrategyTier.INTERMEDIATE,
                        outcome=aster,
                    ).model_dump(mode="json"),
                    StrategyOutcome(
                        strategy_tier=StrategyTier.RADICAL,
                        outcome=hyperliquid,
                        counterfactual=True,
                    ).model_dump(mode="json"),
                ],
            }
        )
    )

    assert flow.state.venue_comparison is not None
    assert flow.state.venue_comparison.matched_signal_keys == ["shared-signal"]
    assert set(flow.state.strategy_summaries) == set(StrategyTier)
    assert flow.state.strategy_summaries[StrategyTier.INTERMEDIATE].executed_count == 1
    assert flow.state.strategy_summaries[StrategyTier.RADICAL].counterfactual_count == 1
    assert (
        flow.state.strategy_summaries[StrategyTier.ULTRA_CONSERVATIVE].sample_count
        == 0
    )


def test_position_lifecycle_flow_closes_only_a_fully_flat_cursor() -> None:
    async def scenario() -> None:
        message = _message()
        repository = InMemoryTradeCursorRepository()
        manager = ConcurrentTradeCursorManager(repository)
        strategy = PositionLifecycleStrategy(
            strategy_tier=StrategyTier.INTERMEDIATE,
            confidence=0.5,
            source_confidence=0.5,
            quality_score=0.5,
            formula_version="test-v1",
            owner_weight=1.0,
            asset_group_weight=1.0,
            position_notional_usd=Decimal("100"),
            leverage=3,
            source=LifecycleStrategySource.INITIAL_CONFIDENCE,
            source_telegram_message_id=message.telegram_message_id,
            selected_at=NOW,
        )
        cursor = await manager.register_exchange_state(
            message,
            ExchangeTradeState(
                exchange_id=ExchangeId.ASTER,
                settlement_asset=SettlementAsset.USDT,
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                active_order_ids={"tp-1"},
                open_position_ids={"position-1"},
                observed_at=NOW,
            ),
            lifecycle_strategy=strategy,
            force_new_cursor=True,
        )
        flow = PositionLifecycleFlow(manager)
        await flow.kickoff_async(
            inputs={
                "cursor_id": cursor.cursor_id,
                "exchange_state": ExchangeTradeState(
                    exchange_id=ExchangeId.ASTER,
                    settlement_asset=SettlementAsset.USDT,
                    symbol="BTCUSDT",
                    direction=PositionDirection.LONG,
                    active_order_ids=set(),
                    open_position_ids=set(),
                    observed_at=NOW,
                ).model_dump(mode="json"),
            }
        )

        assert flow.state.cursor is not None
        assert flow.state.cursor.status == TradeCursorStatus.CLOSED

    asyncio.run(scenario())
