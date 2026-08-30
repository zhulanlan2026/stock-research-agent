from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.outbox.keys import build_effect_key
from stock_research.outbox.store import OutboxStore
from stock_research.stores.models.workflow import OutboxEvent


class OutboxPublisher:
    """正式副作用统一通过 Outbox 发布。"""

    def __init__(self, session: AsyncSession) -> None:
        self.store = OutboxStore(session)

    async def publish(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> OutboxEvent | None:
        effect_key = build_effect_key(aggregate_type, aggregate_id, event_type)
        if await self.store.has_receipt(effect_key):
            return None
        return await self.store.append(
            effect_key=effect_key,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
        )
