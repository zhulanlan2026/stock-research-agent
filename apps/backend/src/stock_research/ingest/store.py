import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.ingest.schemas import IngestEvent
from stock_research.stores.models.workflow import InboxEvent


class IngestStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append_events(self, events: list[IngestEvent]) -> tuple[int, int]:
        received_at = datetime.now(timezone.utc)
        values = [
            {
                "id": uuid.uuid4(),
                "event_id": event.event_id,
                "event_type": event.event_type,
                "payload": event.payload,
                "received_at": received_at,
                "processed_at": None,
            }
            for event in events
        ]

        statement = (
            pg_insert(InboxEvent)
            .values(values)
            .on_conflict_do_nothing(index_elements=["event_id"])
            .returning(InboxEvent.id)
        )
        result = await self.session.execute(statement)
        accepted = len(result.scalars().all())
        duplicates = len(events) - accepted
        return accepted, duplicates
