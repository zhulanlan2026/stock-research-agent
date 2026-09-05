import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class HumanReview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "human_review"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant.id"), index=True, nullable=True
    )
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="REVIEW_REQUIRED", nullable=False
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id"), nullable=True
    )
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)


class HumanReviewEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "human_review_event"

    review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("human_review.id"), index=True
    )
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
