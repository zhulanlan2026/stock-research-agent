from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.decision import DecisionEngine, _decide
from stock_research.fundamental.scenario import ScenarioAssumption
from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore


def test_decide_returns_avoid_for_high_risk() -> None:
    decision, score, rationale = _decide(
        "HIGH",
        Decimal("0.8"),
        Decimal("0.1"),
    )

    assert decision == "AVOID"
    assert score == Decimal("-0.1")
    assert "HIGH" in rationale


def test_decide_returns_attractive_for_low_risk_positive_return() -> None:
    decision, score, _ = _decide(
        "LOW",
        Decimal("0.1"),
        Decimal("0.2"),
    )

    assert decision == "ATTRACTIVE"
    assert score == Decimal("0.2")


def test_decide_returns_insufficient_data_when_missing() -> None:
    decision, score, _ = _decide("UNKNOWN", None, None)

    assert decision == "INSUFFICIENT_DATA"
    assert score is None


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


async def test_decision_engine_combines_risk_and_scenario(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        for metric, value in {
            "total_assets": "200.00",
            "total_liabilities": "50.00",
            "total_equity": "150.00",
            "current_assets": "60.00",
            "current_liabilities": "30.00",
            "operating_cash_flow": "25.00",
            "net_income": "20.00",
            "shares_outstanding": "10.00",
        }.items():
            await store.upsert(_fact(metric, value))
        await session.commit()

        snapshot = await DecisionEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
            [
                ScenarioAssumption("BULL", Decimal("18")),
                ScenarioAssumption("BASE", Decimal("15")),
                ScenarioAssumption("BEAR", Decimal("12")),
            ],
            price=Decimal("25"),
        )

        assert snapshot.module_version == "decision:1.0.0"
        assert snapshot.base_implied_return == Decimal("0.2")
        assert snapshot.decision in {"ATTRACTIVE", "HOLD", "AVOID"}
        assert snapshot.decision_score is not None
