"""Decision persistence adapters for preliminary Flow testing."""

from crewai_app.flows.states import DecisionRecord


class InMemoryDecisionRepository:
    """Idempotent test adapter keyed by CrewAI Flow ID."""

    def __init__(self) -> None:
        self.records: dict[str, DecisionRecord] = {}

    async def save(self, decision: DecisionRecord) -> None:
        existing = self.records.get(decision.flow_id)
        if existing is not None and existing != decision:
            raise ValueError("a Flow decision cannot be overwritten with different data")
        self.records[decision.flow_id] = decision
