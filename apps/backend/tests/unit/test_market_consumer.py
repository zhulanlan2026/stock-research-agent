from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from stock_research.market.consumer import MarketDataConsumer
from stock_research.market.store import MarketBarStore, MarketSnapshotStore
from stock_research.stores.models.workflow import InboxEvent


async def test_consume_pending_persists_snapshot_and_marks_processed(
    db_context: Any,
) -> None:
    async with db_context.factory() as session:
        session.add(
            InboxEvent(
                event_id="evt-1",
                event_type="market.quote",
                payload={"symbol": "600519.SH", "time": 1703228400000, "lastPrice": 9.2},
                received_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        consumed = await MarketDataConsumer(session).consume_pending()
        assert consumed == 1

        snapshots = await MarketSnapshotStore(session).latest("600519.SH")
        assert len(snapshots) == 1
        assert snapshots[0].source_event_id == "evt-1"
        assert snapshots[0].payload["lastPrice"] == 9.2

        inbox = (
            await session.execute(select(InboxEvent).where(InboxEvent.event_id == "evt-1"))
        ).scalar_one()
        assert inbox.processed_at is not None


async def test_consume_pending_persists_market_bar(db_context: Any) -> None:
    async with db_context.factory() as session:
        session.add(
            InboxEvent(
                event_id="bar-1",
                event_type="market.bar",
                payload={
                    "symbol": "600519.SH",
                    "period": "1d",
                    "time": 1703228400000,
                    "open": 10.0,
                    "high": 10.5,
                    "low": 9.9,
                    "close": 10.2,
                    "volume": 1200.0,
                },
                received_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        consumed = await MarketDataConsumer(session).consume_pending()
        assert consumed == 1

        bars = await MarketBarStore(session).latest("600519.SH", "1d")
        assert len(bars) == 1
        assert bars[0].open == 10.0
        assert bars[0].close == 10.2
