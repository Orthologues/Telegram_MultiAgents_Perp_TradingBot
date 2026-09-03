"""CrewAI Flow for one normalized Telegram trading message."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol

from crewai.flow.flow import Flow, listen, start

from frameworkless_app.orchestrator import process_message
from frameworkless_app.telegram_ingestion.deduplication import (
    InMemoryTelegramDeduplicator,
)
from crewai_app.crews.signal_evaluation_crew import SignalEvaluator
from crewai_app.domain.contracts.schemas import (
    ApprovedExecutionRequest,
    ExchangeId,
    ExchangeNetwork,
    FilterDecision,
    MarketAnalysisSnapshot,
    PairRiskLimit,
    QwenSignalHypothesis,
    QwenStrategyCandidateSet,
    SerialRagExample,
    StrategyTier,
    TelegramMessageEnvelope,
    TelegramPromptContext,
    TradeThreadCursor,
)
from crewai_app.domain.lifecycle.cursor import ConcurrentTradeCursorManager
from crewai_app.domain.policies.execution_gate import evaluate_deterministic_risk
from crewai_app.domain.policies.stop_loss import MinistralStopLossPolicy
from crewai_app.flows.states import (
    DecisionRecord,
    DeterministicDecisionOutcome,
    ExecutionLiquiditySnapshot,
    ExecutionMode,
    MinistralStrategyReviewSet,
    TelegramSignalState,
)


class ParentContextLoader(Protocol):
    async def load(self, message: TelegramMessageEnvelope) -> TelegramPromptContext: ...


class CursorContextLoader(Protocol):
    async def load(self, message: TelegramMessageEnvelope) -> list[TradeThreadCursor]: ...


class SerialRagLoader(Protocol):
    async def load(self, message: TelegramMessageEnvelope) -> list[SerialRagExample]: ...


class MarketSnapshotLoader(Protocol):
    async def load(
        self,
        exchange_id: ExchangeId,
        symbol: str,
        reference_price: Decimal,
    ) -> ExecutionLiquiditySnapshot: ...


class DeterministicDecisionService(Protocol):
    async def decide(
        self,
        *,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
        candidates: QwenStrategyCandidateSet,
        reviews: MinistralStrategyReviewSet,
        market_snapshots: Mapping[ExchangeId, ExecutionLiquiditySnapshot],
    ) -> DeterministicDecisionOutcome: ...


class DecisionRepository(Protocol):
    async def save(self, decision: DecisionRecord) -> None: ...


class ExecutionIntentPublisher(Protocol):
    async def publish(self, request: ApprovedExecutionRequest) -> None: ...


class CompatibilityDeterministicDecisionService:
    """Reuse legacy deterministic behavior until its modules are relocated."""

    def __init__(
        self,
        *,
        telegram_deduplicator: InMemoryTelegramDeduplicator | None = None,
        trade_cursor_manager: ConcurrentTradeCursorManager | None = None,
        risk_limits: Mapping[ExchangeId, PairRiskLimit] | None = None,
        existing_position_notional_by_exchange: Mapping[ExchangeId, Decimal] | None = None,
        pair_blacklisted: bool = False,
        tradfi_perpetual_pair: bool = False,
    ) -> None:
        self.telegram_deduplicator = telegram_deduplicator
        self.trade_cursor_manager = trade_cursor_manager
        self.risk_limits = risk_limits
        self.existing_position_notional_by_exchange = (
            existing_position_notional_by_exchange
        )
        self.pair_blacklisted = pair_blacklisted
        self.tradfi_perpetual_pair = tradfi_perpetual_pair

    async def decide(
        self,
        *,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext,
        candidates: QwenStrategyCandidateSet,
        reviews: MinistralStrategyReviewSet,
        market_snapshots: Mapping[ExchangeId, ExecutionLiquiditySnapshot],
    ) -> DeterministicDecisionOutcome:
        if not market_snapshots:
            return DeterministicDecisionOutcome(
                rejection_reasons=["market_snapshot_unavailable"]
            )

        first_snapshot = next(iter(market_snapshots.values()))
        qwen_agent = _PrecomputedQwenAgent(candidates)
        filter_agent = _PrecomputedMinistralAgent(reviews, market_snapshots)
        request = await process_message(
            message,
            qwen_agent,
            filter_agent,
            telegram_deduplicator=self.telegram_deduplicator,
            prompt_context=prompt_context,
            pair_blacklisted=self.pair_blacklisted,
            current_price=first_snapshot.reference_price,
            reference_price=first_snapshot.reference_price,
            market_snapshot=None,
            tradfi_perpetual_pair=self.tradfi_perpetual_pair,
            trade_cursor_manager=self.trade_cursor_manager,
            risk_limits=self.risk_limits,
            existing_position_notional_by_exchange=(
                self.existing_position_notional_by_exchange
            ),
        )
        if request is None:
            return DeterministicDecisionOutcome(
                rejection_reasons=["deterministic_policy_rejected"]
            )
        if request.intent.execution_network != ExchangeNetwork.TESTNET:
            return DeterministicDecisionOutcome(rejection_reasons=["mainnet_disabled"])

        missing = [
            exchange_id.value
            for exchange_id in request.intent.target_exchanges
            if exchange_id not in market_snapshots
        ]
        if missing:
            return DeterministicDecisionOutcome(
                rejection_reasons=[
                    "market_snapshot_unavailable:" + ",".join(sorted(missing))
                ]
            )

        liquidity_rejections = sorted(
            {
                reason
                for exchange_id in request.intent.target_exchanges
                for reason in market_snapshots[exchange_id].rejection_reasons
            }
        )
        if liquidity_rejections:
            return DeterministicDecisionOutcome(
                rejection_reasons=liquidity_rejections
            )

        existing_notional = self.existing_position_notional_by_exchange or {}
        limit_by_exchange = {
            decision.exchange_id: decision.limits for decision in request.risk_decisions
        }
        risk_decisions = [
            evaluate_deterministic_risk(
                request.sizing,
                exchange_id=exchange_id,
                network=request.intent.execution_network,
                symbol=request.intent.symbol,
                limits=limit_by_exchange[exchange_id],
                existing_position_notional_usd=existing_notional.get(
                    exchange_id,
                    Decimal("0"),
                ),
                pair_blacklisted=self.pair_blacklisted,
                instant_order=request.intent.order_type == "market",
                current_price=market_snapshots[exchange_id].market.current_price,
                reference_price=market_snapshots[exchange_id].reference_price,
                asset_group=request.intent.asset_group,
                tradfi_perpetual_pair=self.tradfi_perpetual_pair,
            )
            for exchange_id in request.intent.target_exchanges
        ]
        rejection_reasons = sorted(
            {reason for decision in risk_decisions for reason in decision.reasons}
        )
        if rejection_reasons:
            return DeterministicDecisionOutcome(rejection_reasons=rejection_reasons)
        return DeterministicDecisionOutcome(
            approved_execution_request=request.model_copy(
                update={"risk_decisions": risk_decisions}
            )
        )


class TelegramSignalFlow(Flow[TelegramSignalState]):
    """Dispatch one message through context, Crew, policy, and persistence."""

    initial_state = TelegramSignalState

    def __init__(
        self,
        *,
        parent_context_loader: ParentContextLoader,
        cursor_context_loader: CursorContextLoader,
        serial_rag_loader: SerialRagLoader,
        signal_evaluator: SignalEvaluator,
        market_snapshot_loader: MarketSnapshotLoader,
        deterministic_decision_service: DeterministicDecisionService,
        decision_repository: DecisionRepository,
        execution_intent_publisher: ExecutionIntentPublisher | None = None,
        execution_mode: ExecutionMode | None = None,
        tracing: bool = False,
    ) -> None:
        super().__init__(suppress_flow_events=True, tracing=tracing)
        self.parent_context_loader = parent_context_loader
        self.cursor_context_loader = cursor_context_loader
        self.serial_rag_loader = serial_rag_loader
        self.signal_evaluator = signal_evaluator
        self.market_snapshot_loader = market_snapshot_loader
        self.deterministic_decision_service = deterministic_decision_service
        self.decision_repository = decision_repository
        self.execution_intent_publisher = execution_intent_publisher
        self.execution_mode = execution_mode or ExecutionMode()

    @start()
    async def load_parent_messages(self) -> TelegramPromptContext:
        message = self._message()
        self.state.selected_owner_id = message.owner_id
        self.state.prompt_context = await self.parent_context_loader.load(message)
        if (
            self.state.prompt_context.current_message.telegram_message_id
            != message.telegram_message_id
        ):
            raise ValueError("parent context current message does not match Flow input")
        self.state.trace_steps.append("load_parent_messages")
        return self.state.prompt_context

    @listen(load_parent_messages)
    async def load_active_trade_cursors(self) -> list[TradeThreadCursor]:
        message = self._message()
        cursors = await self.cursor_context_loader.load(message)
        self.state.active_trade_cursors = cursors
        context = self._prompt_context()
        self.state.prompt_context = context.model_copy(
            update={"active_trade_cursors": cursors}
        )
        self.state.trace_steps.append("load_active_trade_cursors")
        return cursors

    @listen(load_active_trade_cursors)
    async def retrieve_owner_rag_examples(self) -> list[SerialRagExample]:
        examples = await self.serial_rag_loader.load(self._message())
        self.state.serial_rag_examples = examples
        self.state.trace_steps.append("retrieve_owner_rag_examples")
        return examples

    @listen(retrieve_owner_rag_examples)
    async def run_signal_evaluation_crew(self) -> QwenStrategyCandidateSet:
        message = self._message()
        if self.state.selected_owner_id != message.owner_id:
            raise ValueError("Flow selected owner does not match the message owner")
        result = await self.signal_evaluator.evaluate(
            message,
            self._prompt_context(),
            self.state.serial_rag_examples,
            self.state.active_trade_cursors,
        )
        if result.candidates.owner_id != message.owner_id:
            raise ValueError("QWEN candidate owner does not match Flow routing")
        self.state.candidate_set = result.candidates
        self.state.ministral_review_set = result.reviews
        self.state.trace_steps.extend(
            ["owner_qwen_inference", "validate_structured_output", "ministral_review"]
        )
        return result.candidates

    @listen(run_signal_evaluation_crew)
    async def load_market_snapshots(self) -> dict[ExchangeId, ExecutionLiquiditySnapshot]:
        candidates = self._candidate_set()
        reviews = self._review_set()
        requested: dict[ExchangeId, tuple[str, Decimal]] = {}
        for tier in StrategyTier:
            review = reviews.reviews[tier]
            intent = review.canonical_intent
            hypothesis = candidates.candidates[tier]
            if review.status != "approved" or intent is None or not hypothesis.entries:
                continue
            for exchange_id in intent.target_exchanges:
                identity = (intent.symbol.upper(), hypothesis.entries[0])
                previous = requested.get(exchange_id)
                if previous is not None and previous != identity:
                    self.state.rejection_reasons.append(
                        f"ambiguous_market_snapshot:{exchange_id.value}"
                    )
                    continue
                requested[exchange_id] = identity

        snapshots = {
            exchange_id: await self.market_snapshot_loader.load(
                exchange_id,
                symbol,
                reference_price,
            )
            for exchange_id, (symbol, reference_price) in requested.items()
        }
        self.state.market_snapshots = snapshots
        self.state.trace_steps.append("load_market_snapshot")
        return snapshots

    @listen(load_market_snapshots)
    async def apply_deterministic_policies(self) -> ApprovedExecutionRequest | None:
        if self.state.rejection_reasons:
            self.state.trace_steps.append("apply_deterministic_policies")
            return None
        outcome = await self.deterministic_decision_service.decide(
            message=self._message(),
            prompt_context=self._prompt_context(),
            candidates=self._candidate_set(),
            reviews=self._review_set(),
            market_snapshots=self.state.market_snapshots,
        )
        self.state.approved_execution_request = outcome.approved_execution_request
        self.state.rejection_reasons.extend(outcome.rejection_reasons)
        self.state.trace_steps.extend(
            ["confidence_selection", "apply_deterministic_policies"]
        )
        return self.state.approved_execution_request

    @listen(apply_deterministic_policies)
    async def persist_decision(self) -> DecisionRecord:
        message = self._message()
        decision = DecisionRecord(
            flow_id=self.state.id,
            owner_id=message.owner_id,
            channel_id=message.channel_id,
            telegram_message_id=message.telegram_message_id,
            approved_execution_request=self.state.approved_execution_request,
            rejection_reasons=list(self.state.rejection_reasons),
            recorded_at=datetime.now(timezone.utc),
        )
        await self.decision_repository.save(decision)
        self.state.decision_record = decision
        self.state.decision_persisted = True
        self.state.trace_steps.append("persist_decision")
        return decision

    @listen(persist_decision)
    async def emit_execution_intent(self) -> ApprovedExecutionRequest | None:
        request = self.state.approved_execution_request
        if request is None or not self.execution_mode.permits(
            request.intent.execution_network
        ):
            return None
        if self.execution_intent_publisher is None:
            self.state.rejection_reasons.append(
                "execution_intent_publisher_unconfigured"
            )
            return None
        await self.execution_intent_publisher.publish(request)
        self.state.execution_intent_emitted = True
        self.state.trace_steps.append("execution_intent")
        return request

    def _message(self) -> TelegramMessageEnvelope:
        if self.state.message is None:
            raise ValueError("TelegramSignalState.message is required")
        return self.state.message

    def _prompt_context(self) -> TelegramPromptContext:
        if self.state.prompt_context is None:
            raise RuntimeError("Telegram prompt context has not been loaded")
        return self.state.prompt_context

    def _candidate_set(self) -> QwenStrategyCandidateSet:
        if self.state.candidate_set is None:
            raise RuntimeError("QWEN candidates have not been produced")
        return self.state.candidate_set

    def _review_set(self) -> MinistralStrategyReviewSet:
        if self.state.ministral_review_set is None:
            raise RuntimeError("Ministral reviews have not been produced")
        return self.state.ministral_review_set


class _PrecomputedQwenAgent:
    def __init__(self, candidates: QwenStrategyCandidateSet) -> None:
        self.candidates = candidates

    async def infer_strategy_candidates(
        self,
        message: TelegramMessageEnvelope,
        prompt_context: TelegramPromptContext | None = None,
    ) -> QwenStrategyCandidateSet:
        return self.candidates


class _PrecomputedMinistralAgent:
    def __init__(
        self,
        reviews: MinistralStrategyReviewSet,
        market_snapshots: Mapping[ExchangeId, ExecutionLiquiditySnapshot],
    ) -> None:
        self.reviews = reviews
        self.market_snapshots = market_snapshots
        self.stop_loss_policy = MinistralStopLossPolicy()

    async def review(
        self,
        hypothesis: QwenSignalHypothesis,
        prompt_context: TelegramPromptContext,
        market_snapshot: MarketAnalysisSnapshot | None = None,
    ) -> FilterDecision:
        review = self.reviews.reviews[hypothesis.strategy_tier]
        policy_market_snapshot = next(
            (
                snapshot.market
                for snapshot in self.market_snapshots.values()
                if hypothesis.symbol is not None
                and snapshot.market.symbol.upper() == hypothesis.symbol.upper()
            ),
            market_snapshot,
        )
        if (
            review.status == "approved"
            and review.canonical_intent is not None
            and review.canonical_intent.stop_loss is None
            and policy_market_snapshot is not None
        ):
            omitted_stop_loss = self.stop_loss_policy.derive(
                hypothesis,
                policy_market_snapshot,
            )
            return review.model_copy(
                update={"omitted_stop_loss": omitted_stop_loss}
            )
        return review
