import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "audit_event"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )


class PolicyDecision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "policy_decision"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("task.id"), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    context_: Mapped[dict[str, object]] = mapped_column(
        "context", JSONB, default=dict, nullable=False
    )
    decided_by: Mapped[str | None] = mapped_column(String(100), nullable=True)


class ModelUsage(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "model_usage"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("task.id"), nullable=True)
    alias: Mapped[str] = mapped_column(String(100), nullable=False)
    actual_model: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(default=0.0, nullable=False)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    cache_hit: Mapped[bool] = mapped_column(default=False, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(200), nullable=True)


class DataAccessLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "data_access_log"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    visibility_scope: Mapped[str | None] = mapped_column(String(50), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
