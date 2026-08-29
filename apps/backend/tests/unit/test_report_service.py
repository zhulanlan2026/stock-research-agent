from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.report import ReportService
from stock_research.fundamental.research import StandardResearchService
from stock_research.fundamental.scenario import ScenarioAssumption
from stock_research.fundamental.schemas import FinancialFactCreate
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


async def test_report_service_renders_all_sections(db_context: Any) -> None:
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

        research = await StandardResearchService(session).run(
            symbol="600519.SH",
            as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
            scenarios=[
                ScenarioAssumption("BULL", Decimal("18")),
                ScenarioAssumption("BASE", Decimal("15")),
                ScenarioAssumption("BEAR", Decimal("12")),
            ],
            price=Decimal("30"),
        )

        report = ReportService().render(research)

        assert report.module_version == "report:1.0.0"
        assert [section.title for section in report.sections] == [
            "概览",
            "估值",
            "情景",
            "风险",
            "同业",
        ]
        valuation = report.sections[1].data
        assert valuation["eps"] == "2"
        assert valuation["pe"] == "15"
        scenarios = report.sections[2].data["scenarios"]
        assert len(scenarios) == 3
        assert scenarios[0]["name"] == "BULL"
