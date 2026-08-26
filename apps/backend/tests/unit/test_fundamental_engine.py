from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.engine import FundamentalEngine
from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore


def _fact(metric: str, value: str) -> FinancialFactCreate:
    return FinancialFactCreate(
        symbol="600519.SH",
        metric=metric,
        period="2025Q4",
        value=Decimal(value),
        unit="CNY",
        source_id="source-1",
        disclosed_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        available_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )


async def test_fundamental_engine_calculates_deterministic_ratios(
    db_context: Any,
) -> None:
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
        }.items():
            await store.upsert(_fact(metric, value))
        await session.commit()

        first = await FundamentalEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        )
        second = await FundamentalEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        )

        assert first == second
        assert first.module_version == "fundamental:1.0.0"
        assert first.metrics["revenue"] == Decimal("100.00")
        assert first.ratios["gross_margin"] == Decimal("0.6")
        assert first.ratios["net_margin"] == Decimal("0.2")
        assert first.ratios["roe"] is not None
        assert first.ratios["roe"].quantize(Decimal("0.001")) == Decimal("0.133")
        assert first.ratios["roa"] == Decimal("0.1")
        assert first.ratios["debt_to_equity"] is not None
        assert first.ratios["debt_to_equity"].quantize(Decimal("0.001")) == Decimal("0.333")
        assert first.ratios["current_ratio"] == Decimal("2")
        assert first.coverage.quantize(Decimal("0.01")) == Decimal("1.00")


async def test_fundamental_engine_marks_missing_metrics_as_none(
    db_context: Any,
) -> None:
    async with db_context.factory() as session:
        await FinancialFactStore(session).upsert(_fact("revenue", "100.00"))
        await session.commit()

        snapshot = await FundamentalEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        )

        assert snapshot.metrics["revenue"] == Decimal("100.00")
        assert snapshot.metrics["net_income"] is None
        assert snapshot.ratios["net_margin"] is None
        assert snapshot.coverage < Decimal("1")
