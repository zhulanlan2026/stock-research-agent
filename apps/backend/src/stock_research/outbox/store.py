import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.workflow import OutboxEvent, SideEffectReceipt


class OutboxStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self,
        *,
        effect_key: str,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> OutboxEvent:
        event = OutboxEvent(
            effect_key=effect_key,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def pending_events(self, limit: int = 100) -> list[OutboxEvent]:
        result = await self.session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.status == "pending")
            .order_by(OutboxEvent.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def has_receipt(self, effect_key: str) -> bool:
        receipt_id = (
            await self.session.execute(
                select(SideEffectReceipt.id)
                .where(SideEffectReceipt.effect_key == effect_key)
                .limit(1)
            )
        ).scalar_one_or_none()
        return receipt_id is not None

    async def mark_sent(self, event_id: uuid.UUID) -> None:
        event = await self.session.get(OutboxEvent, event_id)
        if event is not None:
            event.status = "sent"
            event.sent_at = datetime.now(timezone.utc)

    async def record_receipt(
        self, effect_key: str, receipt_status: str, detail: dict[str, object]
    ) -> SideEffectReceipt:
        receipt = SideEffectReceipt(
            effect_key=effect_key,
            receipt_status=receipt_status,
            detail=detail,
        )
        self.session.add(receipt)
        await self.session.flush()
        return receipt
