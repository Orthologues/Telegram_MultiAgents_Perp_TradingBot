"""Flow-only CrewAI wrapper for deterministic market-snapshot validation."""

from decimal import Decimal

from pydantic import BaseModel, Field

from crewai_app.domain.policies.execution_gate import validate_market_snapshot
from crewai_app.tools._base import TradingBotTool


class MarketSnapshotValidationInput(BaseModel):
    snapshot_symbol: str = Field(min_length=1)
    requested_symbol: str = Field(min_length=1)
    snapshot_reference_price: Decimal = Field(gt=Decimal("0"))
    reference_price: Decimal = Field(gt=Decimal("0"))
    current_price: Decimal = Field(gt=Decimal("0"))


class MarketSnapshotValidationTool(TradingBotTool):
    name: str = "validate_market_snapshot"
    description: str = "Apply deterministic symbol and reference-price execution gates."
    args_schema: type[BaseModel] = MarketSnapshotValidationInput
    agent_accessible: bool = False

    def _run(
        self,
        snapshot_symbol: str,
        requested_symbol: str,
        snapshot_reference_price: Decimal,
        reference_price: Decimal,
        current_price: Decimal,
    ) -> dict[str, bool]:
        validate_market_snapshot(
            snapshot_symbol=snapshot_symbol,
            requested_symbol=requested_symbol,
            snapshot_reference_price=snapshot_reference_price,
            reference_price=reference_price,
            current_price=current_price,
        )
        return {"valid": True}
