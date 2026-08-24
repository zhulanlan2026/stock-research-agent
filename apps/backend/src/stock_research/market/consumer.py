from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.market.store import MarketBarStore, MarketMinuteStateStore, MarketSnapshotStore
from stock_research.stores.models.workflow import InboxEvent

CONSUMABLE_EVENT_TYPES = frozenset({"market.quote", "market.snapshot", "market.bar"})


class MarketDataConsumer:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.store = MarketSnapshotStore(session)
        self.bar_store = MarketBarStore(session)
        self.minute_store = MarketMinuteStateStore(session)

    async def consume_pending(self, limit: int = 100) -> int:
        result = await self.session.execute(
            select(InboxEvent)
            .where(
                InboxEvent.processed_at.is_(None),
                InboxEvent.event_type.in_(CONSUMABLE_EVENT_TYPES),
            )
            .order_by(InboxEvent.id)
            .limit(limit)
        )
        events = list(result.scalars().all())
        for event in events:
            await self._process(event)
        await self.session.commit()
        return len(events)

    async def _process(self, event: InboxEvent) -> None:
        payload = event.payload or {}
        if event.event_type == "market.bar":
            await self._process_bar(event, payload)
            return

        symbol = str(payload.get("symbol") or "UNKNOWN")
        event_time = _event_time(payload, event.received_at)
        await self.store.upsert_from_inbox(
            source_event_id=event.event_id,
            symbol=symbol,
            event_time=event_time,
            payload=payload,
        )
        await self.minute_store.upsert_from_snapshot(
            source_event_id=event.event_id,
            symbol=symbol,
            event_time=event_time,
            payload=payload,
        )
        event.processed_at = datetime.now(timezone.utc)

    async def _process_bar(self, event: InboxEvent, payload: dict[str, object]) -> None:
        symbol = str(payload.get("symbol") or "UNKNOWN")
        period = str(payload.get("period") or "1m")
        bar_time = _event_time(payload, event.received_at)
        open_price = _required_float(payload, "open")
        high = _required_float(payload, "high")
        low = _required_float(payload, "low")
        close = _required_float(payload, "close")
        volume = _optional_float(payload.get("volume"))
        amount = _optional_float(payload.get("amount"))

        await self.bar_store.upsert_from_inbox(
            source_event_id=event.event_id,
            symbol=symbol,
            period=period,
            bar_time=bar_time,
            open_price=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            amount=amount,
        )
        event.processed_at = datetime.now(timezone.utc)


def _event_time(payload: dict[str, object], fallback: datetime | None) -> datetime:
    raw = payload.get("time")
    if isinstance(raw, (int, float)) and raw > 0:
        try:
            return datetime.fromtimestamp(raw / 1000, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            pass

    if fallback is not None:
        return fallback
    return datetime.now(timezone.utc)


def _required_float(payload: dict[str, object], key: str) -> float:
    value = _as_float(payload.get(key))
    if value is None:
        raise ValueError(f"market.bar payload missing numeric field: {key}")
    return value


def _optional_float(value: object) -> float | None:
    return _as_float(value)


def _as_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
