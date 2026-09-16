from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.schemas import FinancialFactCreate
from stock_research.fundamental.store import FinancialFactStore
from stock_research.stores.models.workflow import InboxEvent


class FinancialFactConsumer:
    """消费 inbox 中的 financial.fact 事件并写入 financial_fact。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.store = FinancialFactStore(session)

    async def consume_pending(self, limit: int = 100) -> int:
        result = await self.session.execute(
            select(InboxEvent)
            .where(
                InboxEvent.processed_at.is_(None),
                InboxEvent.event_type == "financial.fact",
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
        now = datetime.now(timezone.utc)
        available_at = _event_time(payload.get("available_at"), now)
        disclosed_at = _event_time(payload.get("disclosed_at"), available_at)
        await self.store.upsert(
            FinancialFactCreate(
                symbol=_required_string(payload, "symbol"),
                metric=_required_string(payload, "metric"),
                period=_required_string(payload, "period"),
                value=_decimal(payload.get("value")),
                unit=str(payload.get("unit") or "CNY").strip(),
                source_id=_required_string(payload, "source_id"),
                disclosed_at=disclosed_at,
                available_at=available_at,
                revision_no=_optional_int(payload.get("revision_no"), 1),
                truth_status=str(payload.get("truth_status") or "VERIFIED").strip(),
                tenant_id=None,
                fact_metadata=_metadata(payload.get("metadata")),
            )
        )
        event.processed_at = now


def _event_time(value: object, fallback: datetime) -> datetime:
    if isinstance(value, (int, float)) and value > 0:
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            pass
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    return fallback


def _required_string(payload: dict[str, object], key: str) -> str:
    value = _optional_string(payload.get(key), None)
    if value is None:
        raise ValueError(f"financial.fact payload missing string field: {key}")
    return value


def _optional_string(value: object, default: str | None) -> str | None:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _optional_int(value: object, default: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("financial.fact value must be numeric")
    try:
        return Decimal(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("financial.fact value must be numeric") from exc


def _metadata(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    return {}
