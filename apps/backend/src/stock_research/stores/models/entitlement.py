import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Plan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "plan"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tier: Mapped[str] = mapped_column(String(50), nullable=False)
    features: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "subscription"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plan.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(nullable=True)


class EntitlementEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "entitlement_event"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plan.id"), nullable=True)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )


class QuotaLedger(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "quota_ledger"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "quota_key", "period", name="uq_quota_ledger"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    quota_key: Mapped[str] = mapped_column(String(100), nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    total: Mapped[int] = mapped_column(default=0, nullable=False)
    used: Mapped[int] = mapped_column(default=0, nullable=False)
    reserved: Mapped[int] = mapped_column(default=0, nullable=False)


class AnalysisSymbolQuota(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "analysis_symbol_quota"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "symbol", "period", name="uq_symbol_quota"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    used_count: Mapped[int] = mapped_column(default=0, nullable=False)
