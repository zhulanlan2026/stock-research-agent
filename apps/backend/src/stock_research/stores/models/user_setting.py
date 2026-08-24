import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_setting"
    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_setting_user_key"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
