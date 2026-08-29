from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.replay import RiskReplayService
from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore


def _fact(value: str) -> FinancialFactCreate:
    return FinancialFactCreate(
        symbol="600519.SH",
        metric="total_equity",
        period="2025Q4",
        value=Decimal(value),
        unit="CNY",
        source_id="source-1",
        disclosed_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        available_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )


async def test_risk_replay_replays_multiple_as_of_points(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        await store.upsert(_fact("150.00"))
        await session.commit()

        as_of_points = [
            datetime(2026, 3, 3, tzinfo=timezone.utc),
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        ]
        first = await RiskReplayService(session).replay("600519.SH", as_of_points)
        second = await RiskReplayService(session).replay("600519.SH", as_of_points)

        assert first.module_version == "risk_replay:1.0.0"
        assert len(first.points) == 2
        assert first.points == second.points


async def test_risk_replay_returns_same_result_for_same_as_of(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        await store.upsert(_fact("150.00"))
        await session.commit()

        as_of = datetime(2026, 4, 1, tzinfo=timezone.utc)
        result = await RiskReplayService(session).replay("600519.SH", [as_of])

        assert result.points[0].as_of == as_of
        assert result.points[0].module_version == "risk:1.0.0"
