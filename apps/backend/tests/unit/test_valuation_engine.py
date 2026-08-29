from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore
from stock_research.fundamental.valuation import ValuationEngine, _valuation_values


def test_valuation_values_compute_market_multiples() -> None:
    metrics: dict[str, Decimal | None] = {
        "revenue": Decimal("100.00"),
        "net_income": Decimal("20.00"),
        "total_equity": Decimal("150.00"),
        "shares_outstanding": Decimal("10.00"),
    }

    per_share, multiples, market_cap = _valuation_values(Decimal("30.00"), metrics)

    assert per_share["eps"] == Decimal("2")
    assert per_share["bvps"] == Decimal("15")
    assert per_share["sps"] == Decimal("10")
    assert multiples["pe"] == Decimal("15")
    assert multiples["pb"] == Decimal("2")
    assert multiples["ps"] == Decimal("3")
    assert market_cap == Decimal("300")


def test_valuation_values_return_none_for_missing_or_zero_inputs() -> None:
    missing: dict[str, Decimal | None] = {
        "revenue": None,
        "net_income": None,
        "total_equity": None,
        "shares_outstanding": None,
    }
    per_share, multiples, market_cap = _valuation_values(Decimal("30.00"), missing)

    assert all(value is None for value in per_share.values())
    assert all(value is None for value in multiples.values())
    assert market_cap is None

    zero_shares: dict[str, Decimal | None] = {
        "revenue": Decimal("100.00"),
        "net_income": Decimal("20.00"),
        "total_equity": Decimal("150.00"),
        "shares_outstanding": Decimal("0"),
    }
    per_share, multiples, market_cap = _valuation_values(Decimal("30.00"), zero_shares)

    assert per_share["eps"] is None
    assert multiples["pe"] is None
    assert market_cap == Decimal("0")


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


async def test_valuation_engine_calculates_from_pit_facts(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        for metric, value in {
            "revenue": "100.00",
            "net_income": "20.00",
            "total_equity": "150.00",
            "shares_outstanding": "10.00",
        }.items():
            await store.upsert(_fact("600519.SH", metric, value))
        await session.commit()

        snapshot = await ValuationEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
            price=Decimal("30.00"),
        )

        assert snapshot.module_version == "valuation:1.0.0"
        assert snapshot.price == Decimal("30.00")
        assert snapshot.shares_outstanding == Decimal("10.00")
        assert snapshot.per_share["eps"] == Decimal("2")
        assert snapshot.multiples["pe"] == Decimal("15")
        assert snapshot.market_cap == Decimal("300")
        assert snapshot.coverage == Decimal("1")


async def test_valuation_engine_marks_missing_shares_as_none(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        await store.upsert(_fact("600519.SH", "net_income", "20.00"))
        await session.commit()

        snapshot = await ValuationEngine(session).calculate(
            "600519.SH",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
            price=Decimal("30.00"),
        )

        assert snapshot.shares_outstanding is None
        assert snapshot.per_share["eps"] is None
        assert snapshot.multiples["pe"] is None
        assert snapshot.market_cap is None
        assert snapshot.coverage < Decimal("1")
