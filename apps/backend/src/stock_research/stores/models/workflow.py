import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Task(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "task"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "idempotency_key", name="uq_task_idempotency"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    as_of: Mapped[datetime | None] = mapped_column(nullable=True)
    requested_modules: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    question: Mapped[str | None] = mapped_column(nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True)


class TaskVersion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "task_version"
    __table_args__ = (UniqueConstraint("task_id", "version_no", name="uq_task_version"),)

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task.id"), index=True)
    version_no: Mapped[int] = mapped_column(nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)


class WorkflowEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_event"
    __table_args__ = (UniqueConstraint("task_id", "sequence_no", name="uq_workflow_event_seq"),)

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task.id"), index=True)
    sequence_no: Mapped[int] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)


class CheckpointRef(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "checkpoint_ref"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task.id"), index=True)
    checkpoint_id: Mapped[str] = mapped_column(String(200), nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    state: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)


class InboxEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "inbox_event"

    event_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class OutboxEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "outbox_event"

    effect_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    available_at: Mapped[datetime | None] = mapped_column(nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)


class SideEffectReceipt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "side_effect_receipt"

    effect_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    receipt_status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
