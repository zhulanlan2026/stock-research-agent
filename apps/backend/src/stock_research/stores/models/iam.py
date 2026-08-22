import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.stores.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tenant"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Identity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "identity"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(320), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Credential(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "credential"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    failed_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(nullable=True)


class Session(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "session"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("device.id"), nullable=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)


class Device(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "device"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    device_key: Mapped[str] = mapped_column(String(200), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "role"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Permission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "permission"

    code: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class UserRole(Base):
    __tablename__ = "user_role"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role.id"), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)


class MfaFactor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "mfa_factor"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), index=True)
    factor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    secret_encrypted: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
