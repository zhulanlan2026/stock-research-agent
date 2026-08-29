from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.scenario import (
    ScenarioAssumption,
    ScenarioEngine,
    _scenario_point,
)
from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore


def test_scenario_point_calculates_target_and_return() -> None:
    point = _scenario_point(
        name="BASE",
        pe=Decimal("15"),
        eps=Decimal("2"),
        current_price=Decimal("30"),
    )

    assert point.target_price == Decimal("30")
    assert point.implied_return == Decimal("0")


def test_scenario_point_returns_none_when_eps_or_price_missing() -> None:
    assert _scenario_point(
        name="BULL",
        pe=Decimal("18"),
        eps=None,
        current_price=Decimal("30"),
    ).target_price is None
    assert _scenario_point(
        name="BEAR",
        pe=Decimal("12"),
        eps=Decimal("2"),
        current_price=None,
    ).implied_return is None


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


async def test_scenario_engine_builds_deterministic_scenarios(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        await store.upsert(_fact("net_income", "20.00"))
        await store.upsert(_fact("shares_outstanding", "10.00"))
        await session.commit()

        snapshot = await ScenarioEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
            [
                ScenarioAssumption("BULL", Decimal("18")),
                ScenarioAssumption("BASE", Decimal("15")),
                ScenarioAssumption("BEAR", Decimal("12")),
            ],
            price=Decimal("30"),
        )

        assert snapshot.module_version == "scenario:1.0.0"
        assert snapshot.current_price == Decimal("30")
        assert snapshot.eps == Decimal("2")
        assert [point.name for point in snapshot.scenarios] == ["BULL", "BASE", "BEAR"]
        assert snapshot.scenarios[0].target_price == Decimal("36")
        assert snapshot.scenarios[1].target_price == Decimal("30")
        assert snapshot.scenarios[2].target_price == Decimal("24")
        assert snapshot.scenarios[0].implied_return == Decimal("0.2")
        assert snapshot.scenarios[2].implied_return == Decimal("-0.2")
