from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.quality import (
    QualityEngine,
    _calculate_quality_ratios,
)
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


def test_quality_ratios_are_deterministic_and_handle_missing_inputs() -> None:
    metrics: dict[str, Decimal | None] = {
        "revenue": Decimal("100.00"),
        "net_income": Decimal("20.00"),
        "total_assets": Decimal("200.00"),
        "total_equity": Decimal("150.00"),
        "current_assets": Decimal("60.00"),
        "current_liabilities": Decimal("30.00"),
        "operating_cash_flow": Decimal("25.00"),
    }

    ratios = _calculate_quality_ratios(metrics)

    assert ratios["accrual_ratio"] == Decimal("-0.025")
    assert ratios["cash_conversion"] == Decimal("1.25")
    assert ratios["operating_cash_flow_margin"] == Decimal("0.25")
    assert ratios["asset_turnover"] == Decimal("0.5")
    equity_multiplier = ratios["equity_multiplier"]
    assert equity_multiplier is not None
    assert equity_multiplier.quantize(Decimal("0.001")) == Decimal("1.333")
    assert ratios["working_capital_to_total_assets"] == Decimal("0.15")

    partial = dict(metrics)
    partial["net_income"] = None
    partial["operating_cash_flow"] = None
    partial["total_assets"] = None
    partial["revenue"] = None
    partial["total_equity"] = None
    partial["current_assets"] = None
    partial["current_liabilities"] = None
    assert all(value is None for value in _calculate_quality_ratios(partial).values())


async def test_quality_engine_calculates_deterministic_ratios(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        for metric, value in {
            "revenue": "100.00",
            "net_income": "20.00",
            "total_assets": "200.00",
            "total_equity": "150.00",
            "current_assets": "60.00",
            "current_liabilities": "30.00",
            "operating_cash_flow": "25.00",
        }.items():
            await store.upsert(_fact(metric, value))
        await session.commit()

        engine = QualityEngine(session)
        first = await engine.calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        )
        second = await engine.calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        )

        assert first == second
        assert first.module_version == "quality:1.0.0"
        assert first.metrics["revenue"] == Decimal("100.00")
        assert first.ratios["accrual_ratio"] == Decimal("-0.025")
        assert first.ratios["cash_conversion"] == Decimal("1.25")
        assert first.coverage == Decimal("1")


async def test_quality_engine_marks_missing_metrics_as_none(db_context: Any) -> None:
    async with db_context.factory() as session:
        await FinancialFactStore(session).upsert(_fact("revenue", "100.00"))
        await session.commit()

        snapshot = await QualityEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        )

        assert snapshot.metrics["revenue"] == Decimal("100.00")
        assert snapshot.metrics["net_income"] is None
        assert snapshot.ratios["cash_conversion"] is None
        assert snapshot.coverage < Decimal("1")
