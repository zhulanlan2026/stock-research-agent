import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FeatureFlag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "feature_flag"
    __table_args__ = (
        UniqueConstraint("key", "environment", name="uq_feature_flag_key_environment"),
    )

    key: Mapped[str] = mapped_column(String(100), nullable=False)
    environment: Mapped[str] = mapped_column(
        String(50), default="production", nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class FeatureFlagRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "feature_flag_rule"
    __table_args__ = (
        UniqueConstraint(
            "flag_id", "rule_type", "rule_value", name="uq_feature_flag_rule"
        ),
    )

    flag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feature_flag.id"), index=True, nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_value: Mapped[str] = mapped_column(String(200), nullable=False)


class FeatureFlagExposure(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "feature_flag_exposure"

    flag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feature_flag.id"), index=True, nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decision: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
