import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.market import MarketBar, MarketMinuteState, MarketSnapshot


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


class MarketMinuteStateStore:
    """按 symbol + as_of_minute 维护一分钟粒度的确定性状态投影。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_from_snapshot(
        self,
        *,
        source_event_id: str,
        symbol: str,
        event_time: datetime,
        payload: dict[str, object],
    ) -> None:
        as_of_minute = event_time.replace(second=0, microsecond=0)
        statement = (
            pg_insert(MarketMinuteState)
            .values(
                id=uuid.uuid4(),
                symbol=symbol,
                as_of_minute=as_of_minute,
                source_event_id=source_event_id,
                payload=payload,
            )
            .on_conflict_do_update(
                index_elements=["symbol", "as_of_minute"],
                set_={
                    "source_event_id": source_event_id,
                    "payload": payload,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        )
        await self.session.execute(statement)

    async def latest(self, symbol: str, limit: int = 20) -> list[MarketMinuteState]:
        result = await self.session.execute(
            select(MarketMinuteState)
            .where(MarketMinuteState.symbol == symbol)
            .order_by(MarketMinuteState.as_of_minute.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
