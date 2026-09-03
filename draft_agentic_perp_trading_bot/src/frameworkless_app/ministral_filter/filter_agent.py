"""Draft Ministral3-8B/14B filter interface."""

from __future__ import annotations

from frameworkless_app.ministral_filter.signal_deduplication import (
    InMemorySignalDeduplicator,
)
from frameworkless_app.ministral_filter.stop_loss_policy import (
    MinistralStopLossPolicy,
)
from frameworkless_app.ministral_filter.take_profit_protection import (
    TakeProfitProtectionPolicy,
)
from frameworkless_app.performance_engine.history import (
    DynamoDBExecutionHistoryRepository,
)
from frameworkless_app.schemas import (
    FilterDecision,
    MarketAnalysisSnapshot,
    OmittedStopLossDecision,
    PositionLifecycleEvent,
    QwenSignalHypothesis,
    TakeProfitFillEvent,
    TakeProfitProtectionDecision,
    TelegramPromptContext,
)


class MinistralFilterAgent:
    def __init__(
        self,
        model_id: str,
        signal_deduplicator: InMemorySignalDeduplicator | None = None,
        stop_loss_policy: MinistralStopLossPolicy | None = None,
        take_profit_protection_policy: TakeProfitProtectionPolicy | None = None,
        execution_history_repository: DynamoDBExecutionHistoryRepository | None = None,
    ):
        self.model_id = model_id
        self.signal_deduplicator = signal_deduplicator
        self.stop_loss_policy = stop_loss_policy or MinistralStopLossPolicy()
        self.take_profit_protection_policy = (
            take_profit_protection_policy or TakeProfitProtectionPolicy()
        )
        self.execution_history_repository = execution_history_repository

    async def record_execution_event(
        self,
        event: PositionLifecycleEvent,
    ) -> None:
        """Persist authenticated execution/P&L metadata through DynamoDB."""
        if self.execution_history_repository is None:
            raise RuntimeError("execution history repository is not configured")
        await self.execution_history_repository.append(event)

    def build_prompt_messages(
        self,
        hypothesis: QwenSignalHypothesis,
        prompt_context: TelegramPromptContext,
        market_snapshot: MarketAnalysisSnapshot | None = None,
        omitted_stop_loss: OmittedStopLossDecision | None = None,
    ) -> list[dict[str, object]]:
        messages = [
            *prompt_context.to_prompt_messages(),
            {"role": "qwen_hypothesis", **hypothesis.model_dump(mode="json")},
        ]
        if market_snapshot is not None:
            messages.append(
                {"role": "mcp_market_snapshot", **market_snapshot.model_dump(mode="json")}
            )
        if omitted_stop_loss is not None:
            messages.append(
                {
                    "role": "deterministic_stop_loss",
                    **omitted_stop_loss.model_dump(mode="json"),
                }
            )
        return messages

    def infer_omitted_stop_loss(
        self,
        hypothesis: QwenSignalHypothesis,
        market_snapshot: MarketAnalysisSnapshot | None,
    ) -> OmittedStopLossDecision | None:
        if market_snapshot is None:
            return None
        return self.stop_loss_policy.derive(hypothesis, market_snapshot)

    async def protect_entry_after_take_profit(
        self,
        event: TakeProfitFillEvent,
    ) -> TakeProfitProtectionDecision:
        """Return an MCP-executable stop adjustment without calling an exchange."""
        return self.take_profit_protection_policy.evaluate(event)

    async def review(
        self,
        hypothesis: QwenSignalHypothesis,
        prompt_context: TelegramPromptContext,
        market_snapshot: MarketAnalysisSnapshot | None = None,
    ) -> FilterDecision:
        """Validate, deduplicate, quality-score, and canonicalize a QWEN hypothesis."""
        deduplication = None
        if self.signal_deduplicator is not None:
            deduplication = self.signal_deduplicator.check(hypothesis)
            if deduplication.is_duplicate:
                return FilterDecision(
                    status="rejected",
                    quality_score=0.0,
                    canonical_intent=None,
                    rejection_reasons=deduplication.reasons,
                    reviewer_model=self.model_id,
                    deduplication=deduplication,
                )

        omitted_stop_loss = self.infer_omitted_stop_loss(
            hypothesis,
            market_snapshot,
        )
        _ = self.build_prompt_messages(
            hypothesis,
            prompt_context,
            market_snapshot,
            omitted_stop_loss,
        )
        return FilterDecision(
            status="rejected",
            quality_score=0.0,
            canonical_intent=None,
            rejection_reasons=["placeholder implementation"],
            reviewer_model=self.model_id,
            deduplication=deduplication,
            omitted_stop_loss=omitted_stop_loss,
        )
