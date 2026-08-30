from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.supply_chain import Order, OrderStatusEvent

VALID_TRANSITIONS = {
    "CREATED": {"CONFIRMED", "CANCELED"},
    "CONFIRMED": {"SHIPPED", "CANCELED"},
    "SHIPPED": {"DELIVERED"},
    "DELIVERED": {"COMPLETED"},
}


class OrderLifecycleService:
    """确定性订单状态流转。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def transition(
        self,
        order: Order,
        to_status: str,
        *,
        reason: str | None = None,
        event_time: datetime | None = None,
    ) -> OrderStatusEvent:
        allowed = VALID_TRANSITIONS.get(order.status, set())
        if to_status not in allowed:
            raise ValueError(
                f"invalid order transition: {order.status} -> {to_status}"
            )

        event_time = event_time or datetime.now(timezone.utc)
        event = OrderStatusEvent(
            order_id=order.id,
            from_status=order.status,
            to_status=to_status,
            event_time=event_time,
            reason=reason,
        )
        order.status = to_status
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event
