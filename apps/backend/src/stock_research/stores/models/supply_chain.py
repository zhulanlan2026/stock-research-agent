import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Contract(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "contract"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant.id"), index=True, nullable=True
    )
    subject_org: Mapped[str] = mapped_column(String(200), nullable=False)
    object_org: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 12), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)


class Order(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "order"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant.id"), index=True, nullable=True
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contract.id"), index=True
    )
    order_no: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 12), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", nullable=False)


class OrderStatusEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "order_status_event"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order.id"), index=True
    )
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
