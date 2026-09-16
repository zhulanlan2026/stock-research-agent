from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.professional import ProfessionalFinancialEngine
from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore


def _fact(metric: str, period: str, value: str) -> FinancialFactCreate:
    return FinancialFactCreate(
        symbol="600519.SH",
        metric=metric,
        period=period,
        value=Decimal(value),
        unit="CNY",
        source_id=f"professional-{metric}-{period}",
        disclosed_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        available_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )


async def test_professional_financial_engine_calculates_growth_and_dupont(
    db_context: Any,
) -> None:
    current = {
        "revenue": "1200.00",
        "cost_of_revenue": "450.00",
        "operating_income": "300.00",
        "net_income": "250.00",
        "total_assets": "2500.00",
        "total_liabilities": "900.00",
        "total_equity": "1600.00",
        "current_assets": "700.00",
        "current_liabilities": "320.00",
        "inventory": "180.00",
        "operating_cash_flow": "300.00",
        "capital_expenditure": "80.00",
        "interest_expense": "20.00",
    }
    previous = {
        "revenue": "1000.00",
        "cost_of_revenue": "400.00",
        "operating_income": "220.00",
        "net_income": "200.00",
        "total_assets": "2300.00",
        "total_liabilities": "800.00",
        "total_equity": "1500.00",
        "current_assets": "600.00",
        "current_liabilities": "300.00",
        "inventory": "170.00",
        "operating_cash_flow": "260.00",
        "capital_expenditure": "70.00",
        "interest_expense": "25.00",
    }

    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        for metric, value in current.items():
            await store.upsert(_fact(metric, "2025Q4", value))
        for metric, value in previous.items():
            await store.upsert(_fact(metric, "2025Q3", value))
        await session.commit()

        snapshot = await ProfessionalFinancialEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        )

    assert snapshot.module_version == "professional_financial:1.0.0"
    assert snapshot.coverage == Decimal("1")
    assert snapshot.growth["revenue"] == Decimal("0.2")
    assert snapshot.growth["net_income"] == Decimal("0.25")
    assert snapshot.dupont["net_margin"] == Decimal("0.2083333333333333333333333333")
    assert snapshot.free_cash_flow == Decimal("220")
    assert snapshot.ratios["quick_ratio"] == Decimal("1.625")
    assert snapshot.ratios["interest_coverage"] == Decimal("15")
    assert snapshot.risk_points == ()
