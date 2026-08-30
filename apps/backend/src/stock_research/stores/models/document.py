import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant.id"), index=True, nullable=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id"), index=True, nullable=True
    )
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="UPLOADED", nullable=False)
    source_level: Mapped[str | None] = mapped_column(String(8), nullable=True)
    external_model_allowed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )


class DocumentVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_version"
    __table_args__ = (
        UniqueConstraint("document_id", "version_no", name="uq_document_version"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document.id"), index=True
    )
    version_no: Mapped[int] = mapped_column(nullable=False)
    raw_object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    parser: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="UPLOADED", nullable=False)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NormalizedBlock(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "normalized_block"

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_version.id"), index=True
    )
    page_start: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    section: Mapped[str] = mapped_column(String(200), nullable=False)
    block_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    block_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
