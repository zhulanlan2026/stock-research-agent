from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.scenario import ScenarioAssumption
from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.snapshot import SnapshotEngine
from stock_research.fundamental.store import FinancialFactStore


def _fact(metric: str, value: str) -> FinancialFactCreate:
    return FinancialFactCreate(
        symbol="600519.SH",
        metric=metric,
        period="2025Q4",
        value=Decimal(value),
        unit="shares" if metric == "shares_outstanding" else "CNY",
        source_id="source-1",
        disclosed_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        available_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )


async def test_snapshot_engine_aggregates_all_modules(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        for metric, value in {
            "revenue": "100.00",
            "cost_of_revenue": "40.00",
            "net_income": "20.00",
            "total_assets": "200.00",
            "total_liabilities": "50.00",
            "total_equity": "150.00",
            "current_assets": "60.00",
            "current_liabilities": "30.00",
            "operating_cash_flow": "25.00",
            "shares_outstanding": "10.00",
        }.items():
            await store.upsert(_fact(metric, value))
        await session.commit()

        scenarios = [
            ScenarioAssumption("BULL", Decimal("18")),
            ScenarioAssumption("BASE", Decimal("15")),
            ScenarioAssumption("BEAR", Decimal("12")),
        ]
        snapshot = await SnapshotEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
            scenarios,
            price=Decimal("30"),
        )

        assert snapshot.module_version == "snapshot:1.0.0"
        assert snapshot.fundamental.module_version == "fundamental:1.0.0"
        assert snapshot.quality.module_version == "quality:1.0.0"
        assert snapshot.valuation.module_version == "valuation:1.0.0"
        assert snapshot.risk.module_version == "risk:1.0.0"
        assert snapshot.scenario is not None
        assert snapshot.decision is not None
        assert snapshot.coverage.quantize(Decimal("0.01")) == Decimal("0.94")


async def test_snapshot_engine_is_deterministic(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        await store.upsert(_fact("net_income", "20.00"))
        await store.upsert(_fact("shares_outstanding", "10.00"))
        await session.commit()

        scenarios = [ScenarioAssumption("BASE", Decimal("15"))]
        first = await SnapshotEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
            scenarios,
            price=Decimal("30"),
        )
        second = await SnapshotEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
            scenarios,
            price=Decimal("30"),
        )

        assert first == second
