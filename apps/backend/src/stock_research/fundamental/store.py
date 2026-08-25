import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.stores.models.fundamental import FinancialFact


class FinancialFactStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, fact: FinancialFactCreate) -> FinancialFact:
        statement = (
            pg_insert(FinancialFact)
            .values(
                id=uuid.uuid4(),
                tenant_id=fact.tenant_id,
                symbol=fact.symbol,
                metric=fact.metric,
                period=fact.period,
                value=fact.value,
                unit=fact.unit,
                source_id=fact.source_id,
                disclosed_at=fact.disclosed_at,
                available_at=fact.available_at,
                revision_no=fact.revision_no,
                truth_status=fact.truth_status,
                fact_metadata=fact.fact_metadata,
            )
            .on_conflict_do_update(
                index_elements=["source_id", "symbol", "metric", "period", "revision_no"],
                set_={
                    "value": fact.value,
                    "unit": fact.unit,
                    "disclosed_at": fact.disclosed_at,
                    "available_at": fact.available_at,
                    "truth_status": fact.truth_status,
                    "metadata": fact.fact_metadata,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            .returning(FinancialFact)
        )
        result = await self.session.execute(statement)
        fact_row = result.scalar_one()
        await self.session.refresh(fact_row)
        return fact_row

    async def latest(
        self,
        *,
        symbol: str,
        metric: str,
        as_of: datetime,
        period: str | None = None,
        truth_status: str = "VERIFIED",
    ) -> FinancialFact | None:
        query = select(FinancialFact).where(
            FinancialFact.symbol == symbol,
            FinancialFact.metric == metric,
            FinancialFact.available_at <= as_of,
            FinancialFact.truth_status == truth_status,
        )
        if period is not None:
            query = query.where(FinancialFact.period == period)
        query = query.order_by(
            FinancialFact.available_at.desc(),
            FinancialFact.revision_no.desc(),
        ).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
