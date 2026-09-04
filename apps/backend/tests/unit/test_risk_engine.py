from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.risk import (
    RiskEngine,
    _financial_ratios,
    _market_risk,
    _risk_action,
    _risk_classification,
)
from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore


class _Bar:
    def __init__(self, close: float) -> None:
        self.close = close


def test_financial_ratios_are_deterministic() -> None:
    ratios = _financial_ratios(
        {
            "total_assets": Decimal("200"),
            "total_liabilities": Decimal("50"),
            "total_equity": Decimal("150"),
            "current_assets": Decimal("60"),
            "current_liabilities": Decimal("30"),
            "operating_cash_flow": Decimal("25"),
        }
    )

    assert ratios["leverage_ratio"] == Decimal("0.3333333333333333333333333333")
    assert ratios["equity_ratio"] == Decimal("0.75")
    assert ratios["current_ratio"] == Decimal("2")
    assert ratios["cash_flow_to_current_liabilities"] == Decimal(
        "0.8333333333333333333333333333"
    )


def test_market_risk_handles_missing_or_zero_returns() -> None:
    assert _market_risk([_Bar(10.0)]) == {
        "annualized_volatility": None,
        "max_drawdown": None,
    }
    result = _market_risk([_Bar(10.0), _Bar(10.0)])
    assert result["annualized_volatility"] == Decimal("0")
    assert result["max_drawdown"] == Decimal("0")


def test_risk_classification_uses_available_components() -> None:
    financial_ratios = {
        "leverage_ratio": Decimal("3"),
        "current_ratio": Decimal("0.5"),
        "cash_flow_to_current_liabilities": Decimal("-1"),
    }
    market_risk = {
        "annualized_volatility": Decimal("0.9"),
        "max_drawdown": Decimal("0.2"),
    }

    score, level, coverage = _risk_classification(financial_ratios, market_risk)

    assert level == "HIGH"
    assert score is not None
    assert score.quantize(Decimal("0.01")) == Decimal("0.94")
    assert coverage == Decimal("1")


def test_risk_classification_returns_unknown_without_components() -> None:
    financial_ratios = {
        "leverage_ratio": None,
        "current_ratio": None,
        "cash_flow_to_current_liabilities": None,
    }
    market_risk = {
        "annualized_volatility": None,
        "max_drawdown": None,
    }

    score, level, coverage = _risk_classification(financial_ratios, market_risk)
    assert score is None
    assert level == "UNKNOWN"
    assert coverage == Decimal("0")


def test_risk_action_maps_level_to_action() -> None:
    assert _risk_action("LOW") == "WATCH"
    assert _risk_action("MEDIUM") == "RESTRICT"
    assert _risk_action("HIGH") == "BLOCK"
    assert _risk_action("UNKNOWN") == "WATCH"


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


async def test_risk_engine_builds_financial_risk_without_market_data(
    db_context: Any,
) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        for metric, value in {
            "total_assets": "200.00",
            "total_liabilities": "50.00",
            "total_equity": "150.00",
            "current_assets": "60.00",
            "current_liabilities": "30.00",
            "operating_cash_flow": "25.00",
        }.items():
            await store.upsert(_fact(metric, value))
        await session.commit()

        snapshot = await RiskEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
        )

        assert snapshot.module_version == "risk:1.0.0"
        assert snapshot.financial_ratios["leverage_ratio"] is not None
        assert snapshot.financial_ratios["current_ratio"] == Decimal("2")
        assert snapshot.market_risk["annualized_volatility"] is None
        assert snapshot.risk_level in {"LOW", "MEDIUM", "HIGH"}
        assert snapshot.coverage < Decimal("1")
