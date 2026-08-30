import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Evidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "evidence"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant.id"), index=True, nullable=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document.id"), index=True, nullable=True
    )
    document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_version.id"), index=True, nullable=True
    )
    root_evidence_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_level: Mapped[str | None] = mapped_column(String(8), nullable=True)
    citation_ready: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    authorization: Mapped[dict[str, object]] = mapped_column(
        JSONB, default=dict, nullable=False
    )


class Claim(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "claim"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenant.id"), index=True, nullable=True
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    predicate: Mapped[str] = mapped_column(String(200), nullable=False)
    object: Mapped[str] = mapped_column(String(500), nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(32), default="DRAFT", nullable=False
    )
    confidence: Mapped[Decimal] = mapped_column(Float, default=0.0, nullable=False)
