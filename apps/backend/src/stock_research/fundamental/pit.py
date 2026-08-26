from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.store import FinancialFactStore
from stock_research.stores.models.fundamental import FinancialFact


@dataclass(frozen=True)
class ResolvedFinancialFact:
    symbol: str
    metric: str
    period: str
    value: Decimal
    unit: str
    source_id: str
    disclosed_at: datetime
    available_at: datetime
    revision_no: int
    truth_status: str
    fact: FinancialFact


class PitResolver:
    """按 as_of 点时间口径解析最新可用 financial_fact。"""

    def __init__(self, session: AsyncSession) -> None:
        self.store = FinancialFactStore(session)

    async def resolve(
        self,
        *,
        symbol: str,
        metric: str,
        as_of: datetime,
        period: str | None = None,
    ) -> ResolvedFinancialFact | None:
        fact = await self.store.latest(
            symbol=symbol,
            metric=metric,
            as_of=as_of,
            period=period,
        )
        if fact is None:
            return None
        return self._to_resolved(fact)

    def _to_resolved(self, fact: FinancialFact) -> ResolvedFinancialFact:
        return ResolvedFinancialFact(
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
            fact=fact,
        )
