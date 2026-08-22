from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.outbox.registry import HandlerRegistry
from stock_research.outbox.store import OutboxStore


class OutboxDispatcher:
    def __init__(self, session: AsyncSession, registry: HandlerRegistry) -> None:
        self.session = session
        self.store = OutboxStore(session)
        self.registry = registry

    async def dispatch_pending(self, limit: int = 100) -> int:
        events = await self.store.pending_events(limit)
        dispatched = 0
        for event in events:
            if await self.store.has_receipt(event.effect_key):
                await self.store.mark_sent(event.id)
                continue

            handler = self.registry.get(event.event_type)
            if handler is None:
                event.status = "failed"
                continue

            event.status = "processing"
            event.attempts += 1
            await self.session.flush()
            try:
                await handler(event.payload)
                await self.store.mark_sent(event.id)
                await self.store.record_receipt(event.effect_key, "ok", {})
                dispatched += 1
            except Exception:
                event.status = "pending"
                await self.session.flush()

        await self.session.commit()
        return dispatched
