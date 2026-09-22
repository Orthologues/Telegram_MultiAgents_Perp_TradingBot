"""Decision persistence adapters for preliminary Flow testing."""

from crewai_app.domain.contracts.schemas import DecisionRecord
from crewai_app.flows.interfaces import DecisionRepository


class InMemoryDecisionRepository(DecisionRepository):
    """Idempotent test adapter keyed by message/execution identity."""

    def __init__(self) -> None:
        self.records: dict[str, DecisionRecord] = {}
        self._records_by_idempotency_key: dict[str, DecisionRecord] = {}

    async def save(self, decision: DecisionRecord) -> None:
        existing = self._records_by_idempotency_key.get(decision.idempotency_key)
        if existing is not None:
            if not _same_idempotent_decision(existing, decision):
                raise ValueError("an idempotency key cannot be overwritten with different data")
            self.records[decision.flow_id] = existing
            return
        flow_existing = self.records.get(decision.flow_id)
        if flow_existing is not None and not _same_idempotent_decision(
            flow_existing,
            decision,
        ):
            raise ValueError("a Flow decision cannot be overwritten with different data")
        self._records_by_idempotency_key[decision.idempotency_key] = decision
        self.records[decision.flow_id] = decision

    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> DecisionRecord | None:
        return self._records_by_idempotency_key.get(idempotency_key)


def _same_idempotent_decision(
    first: DecisionRecord,
    second: DecisionRecord,
) -> bool:
    return first.model_dump(mode="python", exclude={"flow_id", "recorded_at"}) == second.model_dump(
        mode="python",
        exclude={"flow_id", "recorded_at"},
    )
