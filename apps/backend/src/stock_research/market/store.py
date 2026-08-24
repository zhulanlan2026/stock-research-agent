import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.market import MarketBar, MarketSnapshot


class MarketSnapshotStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_from_inbox(
        self,
        *,
        source_event_id: str,
        symbol: str,
        event_time: datetime,
        payload: dict[str, object],
    ) -> None:
        statement = (
            pg_insert(MarketSnapshot)
            .values(
                id=uuid.uuid4(),
                symbol=symbol,
                source_event_id=source_event_id,
                event_time=event_time,
                payload=payload,
            )
            .on_conflict_do_nothing(index_elements=["source_event_id"])
        )
        await self.session.execute(statement)

    async def latest(self, symbol: str, limit: int = 20) -> list[MarketSnapshot]:
        result = await self.session.execute(
            select(MarketSnapshot)
            .where(MarketSnapshot.symbol == symbol)
            .order_by(MarketSnapshot.event_time.desc(), MarketSnapshot.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class MarketBarStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_from_inbox(
        self,
        *,
        source_event_id: str,
        symbol: str,
        period: str,
        bar_time: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float | None,
        amount: float | None,
    ) -> None:
        statement = (
            pg_insert(MarketBar)
            .values(
                id=uuid.uuid4(),
                symbol=symbol,
                period=period,
                bar_time=bar_time,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                amount=amount,
                source_event_id=source_event_id,
            )
            # 同时容忍 source_event_id 与 (symbol, period, bar_time) 的唯一冲突，
            # 避免不同 event_id 但同一根 K 线导致整批消费失败。
            .on_conflict_do_nothing()
        )
        await self.session.execute(statement)

    async def latest(self, symbol: str, period: str, limit: int = 100) -> list[MarketBar]:
        result = await self.session.execute(
            select(MarketBar)
            .where(MarketBar.symbol == symbol, MarketBar.period == period)
            .order_by(MarketBar.bar_time.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
