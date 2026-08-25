import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FinancialFact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "financial_fact"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "symbol",
            "metric",
            "period",
            "revision_no",
            name="uq_financial_fact_source_symbol_metric_period_revision",
        ),
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant.id"), index=True, nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    metric: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(38, 12), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(200), nullable=False)
    disclosed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    revision_no: Mapped[int] = mapped_column(nullable=False, default=1)
    truth_status: Mapped[str] = mapped_column(String(32), default="VERIFIED", nullable=False)
    fact_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
