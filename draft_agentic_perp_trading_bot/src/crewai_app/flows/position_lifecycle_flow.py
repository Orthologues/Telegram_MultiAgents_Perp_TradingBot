"""CrewAI Flow for deterministic trade-cursor lifecycle refreshes."""

from __future__ import annotations

from crewai.flow.flow import Flow, start

from crewai_app.domain.contracts.schemas import TradeThreadCursor
from crewai_app.domain.lifecycle.cursor import ConcurrentTradeCursorManager
from crewai_app.flows.states import PositionLifecycleState


class PositionLifecycleFlow(Flow[PositionLifecycleState]):
    """Refresh a cursor and close it only after positions and orders are gone."""

    initial_state = PositionLifecycleState

    def __init__(
        self,
        cursor_manager: ConcurrentTradeCursorManager,
        *,
        tracing: bool = False,
    ) -> None:
        super().__init__(suppress_flow_events=True, tracing=tracing)
        self.cursor_manager = cursor_manager

    @start()
    async def refresh_cursor(self) -> TradeThreadCursor:
        if not self.state.cursor_id:
            raise ValueError("PositionLifecycleState.cursor_id is required")
        if self.state.exchange_state is None:
            raise ValueError("PositionLifecycleState.exchange_state is required")
        self.state.cursor = await self.cursor_manager.refresh_exchange_state(
            self.state.cursor_id,
            self.state.exchange_state,
        )
        return self.state.cursor
