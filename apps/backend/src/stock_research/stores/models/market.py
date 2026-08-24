from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MarketSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "market_snapshot"

    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)


class MarketBar(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "market_bar"
    __table_args__ = (
        UniqueConstraint("symbol", "period", "bar_time", name="uq_market_bar_symbol_period_time"),
    )

    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(8), nullable=False)
    bar_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    open: Mapped[float] = mapped_column(nullable=False)
    high: Mapped[float] = mapped_column(nullable=False)
    low: Mapped[float] = mapped_column(nullable=False)
    close: Mapped[float] = mapped_column(nullable=False)
    volume: Mapped[float | None] = mapped_column(nullable=True)
    amount: Mapped[float | None] = mapped_column(nullable=True)
    source_event_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
