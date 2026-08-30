from typing import Any

from stock_research.outbox.publisher import OutboxPublisher
from stock_research.outbox.store import OutboxStore


async def test_outbox_publisher_appends_formal_event(db_context: Any) -> None:
    async with db_context.factory() as session:
        publisher = OutboxPublisher(session)
        event = await publisher.publish(
            aggregate_type="report",
            aggregate_id="report-1",
            event_type="published",
            payload={"symbol": "600519.SH"},
        )
        await session.commit()

        assert event is not None
        assert event.effect_key == "report:report-1:published"
        assert await OutboxStore(session).has_receipt(event.effect_key) is False


async def test_outbox_publisher_deduplicates_by_receipt(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = OutboxStore(session)
        await store.record_receipt("report:report-1:published", "ok", {})
        await session.commit()

        event = await OutboxPublisher(session).publish(
            aggregate_type="report",
            aggregate_id="report-1",
            event_type="published",
            payload={},
        )

        assert event is None
