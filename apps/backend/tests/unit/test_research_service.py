from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.research import StandardResearchService
from stock_research.fundamental.scenario import ScenarioAssumption
from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore


def _fact(symbol: str, metric: str, value: str) -> FinancialFactCreate:
    return FinancialFactCreate(
        symbol=symbol,
        metric=metric,
        period="2025Q4",
        value=Decimal(value),
        unit="shares" if metric == "shares_outstanding" else "CNY",
        source_id=f"source-{symbol}",
        disclosed_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        available_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )


async def test_standard_research_runs_all_deterministic_modules(
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
            "shares_outstanding": "10.00",
        }.items():
            await store.upsert(_fact("600519.SH", metric, value))
        await session.commit()

        scenarios = [ScenarioAssumption("BASE", Decimal("15"))]
        result = await StandardResearchService(session).run(
            symbol="600519.SH",
            as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
            scenarios=scenarios,
            price=Decimal("30"),
        )

        assert result.module_version == "standard_research:1.0.0"
        assert result.status == "COMPLETED"
        assert result.snapshot.module_version == "snapshot:1.0.0"
        assert result.peer_comparison is None
        assert result.coverage is not None


async def test_standard_research_includes_peer_comparison_when_requested(
    db_context: Any,
) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        for symbol, net_income, total_equity in (
            ("600519.SH", "20.00", "150.00"),
            ("000858.SZ", "10.00", "100.00"),
        ):
            await store.upsert(_fact(symbol, "net_income", net_income))
            await store.upsert(_fact(symbol, "total_equity", total_equity))
        await session.commit()

        scenarios = [ScenarioAssumption("BASE", Decimal("15"))]
        result = await StandardResearchService(session).run(
            symbol="600519.SH",
            as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
            scenarios=scenarios,
            peers=["000858.SZ"],
            price=Decimal("30"),
        )

        assert result.peer_comparison is not None
        assert result.peer_comparison.symbol == "600519.SH"
