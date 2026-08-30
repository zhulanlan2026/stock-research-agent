from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.agents.report_agent import ReportAgent
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


async def test_report_agent_renders_report(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        await store.upsert(_fact("net_income", "20.00"))
        await store.upsert(_fact("shares_outstanding", "10.00"))
        await session.commit()

        research = await StandardResearchService(session).run(
            symbol="600519.SH",
            as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
            scenarios=[ScenarioAssumption("BASE", Decimal("15"))],
            price=Decimal("30"),
        )
        result = await ReportAgent().run(research)

        assert result.agent == "report"
        assert result.report.sections
