from typing import Any

from sqlalchemy import func, select

from stock_research.outbox.dispatcher import OutboxDispatcher
from stock_research.outbox.publisher import OutboxPublisher
from stock_research.outbox.registry import HandlerRegistry
from stock_research.stores.models.workflow import OutboxEvent


async def test_duplicate_publish_produces_single_outbox_event(db_context: Any) -> None:
    async with db_context.factory() as session:
        publisher = OutboxPublisher(session)
        first = await publisher.publish(
            aggregate_type="report",
            aggregate_id="report-1",
            event_type="published",
            payload={"symbol": "600519.SH"},
        )
        second = await publisher.publish(
            aggregate_type="report",
            aggregate_id="report-1",
            event_type="published",
            payload={"symbol": "600519.SH"},
        )
        await session.commit()

        assert first is not None
        assert second is None

        count = await session.scalar(
            select(func.count())
            .select_from(OutboxEvent)
            .where(OutboxEvent.effect_key == "report:report-1:published")
        )
        assert count == 1


async def test_dispatch_does_not_repeat_formal_side_effect(db_context: Any) -> None:
    calls: list[dict[str, object]] = []

    async def handler(payload: dict[str, object]) -> None:
        calls.append(payload)

    registry = HandlerRegistry()
    registry.register("published", handler)

    async with db_context.factory() as session:
        await OutboxPublisher(session).publish(
            aggregate_type="report",
            aggregate_id="report-1",
            event_type="published",
            payload={"symbol": "600519.SH"},
        )
        await session.commit()

    async with db_context.factory() as session:
        assert await OutboxDispatcher(session, registry).dispatch_pending() == 1

    async with db_context.factory() as session:
        assert await OutboxDispatcher(session, registry).dispatch_pending() == 0

    assert len(calls) == 1
