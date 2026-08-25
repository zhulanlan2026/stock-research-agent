from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from stock_research.fundamental.pit import PitResolver
from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore
from stock_research.stores.models.fundamental import FinancialFact


def _fact(
    *,
    period: str = "2025Q4",
    value: str = "100.00",
    revision_no: int = 1,
    available_at: datetime | None = None,
) -> FinancialFactCreate:
    return FinancialFactCreate(
        symbol="600519.SH",
        metric="revenue",
        period=period,
        value=Decimal(value),
        unit="CNY",
        source_id="source-1",
        disclosed_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        available_at=available_at or datetime(2026, 3, 2, tzinfo=timezone.utc),
        revision_no=revision_no,
    )


async def test_financial_fact_upsert_is_idempotent(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)

        first = await store.upsert(_fact())
        second = await store.upsert(
            _fact(value="101.00", available_at=datetime(2026, 3, 3, tzinfo=timezone.utc))
        )

        facts = (
            await session.execute(
                select(FinancialFact).where(FinancialFact.symbol == "600519.SH")
            )
        ).scalars().all()

        assert len(facts) == 1
        assert first.id == second.id
        assert second.value == Decimal("101.00")


async def test_pit_resolver_uses_point_in_time_available_at(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        await store.upsert(
            _fact(
                period="2025Q3",
                value="90.00",
                available_at=datetime(2025, 11, 1, tzinfo=timezone.utc),
            )
        )
        await store.upsert(
            _fact(
                period="2025Q4",
                value="100.00",
                available_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
            )
        )
        await session.commit()

        resolver = PitResolver(session)
        before_q4 = await resolver.resolve(
            symbol="600519.SH",
            metric="revenue",
            as_of=datetime(2025, 12, 31, tzinfo=timezone.utc),
        )
        after_q4 = await resolver.resolve(
            symbol="600519.SH",
            metric="revenue",
            as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        )

        assert before_q4 is not None
        assert before_q4.period == "2025Q3"
        assert before_q4.value == Decimal("90.00")
        assert after_q4 is not None
        assert after_q4.period == "2025Q4"
        assert after_q4.value == Decimal("100.00")


async def test_pit_resolver_prefers_latest_revision(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FinancialFactStore(session)
        await store.upsert(_fact(value="100.00", revision_no=1))
        await store.upsert(_fact(value="101.00", revision_no=2))
        await session.commit()

        resolved = await PitResolver(session).resolve(
            symbol="600519.SH",
            metric="revenue",
            as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        )

        assert resolved is not None
        assert resolved.revision_no == 2
        assert resolved.value == Decimal("101.00")


async def test_pit_resolver_returns_none_before_available(db_context: Any) -> None:
    async with db_context.factory() as session:
        await FinancialFactStore(session).upsert(_fact())
        await session.commit()

        resolved = await PitResolver(session).resolve(
            symbol="600519.SH",
            metric="revenue",
            as_of=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        assert resolved is None
