import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth import security
from stock_research.auth.errors import AuthError
from stock_research.core.config import get_settings
from stock_research.stores.models.iam import Credential, Session, Tenant, User


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def login(
        self, email: str, password: str, tenant_slug: str | None
    ) -> tuple[str, str, User]:
        user = await self._find_user(email, tenant_slug)
        if user is None:
            raise AuthError("AUTH_INVALID_CREDENTIALS", "账号或密码错误")

        credential = (
            await self.session.execute(select(Credential).where(Credential.user_id == user.id))
        ).scalar_one_or_none()
        if credential is None:
            raise AuthError("AUTH_INVALID_CREDENTIALS", "账号或密码错误")

        now = datetime.now(timezone.utc)
        if credential.locked_until is not None and credential.locked_until > now:
            raise AuthError("AUTH_INVALID_CREDENTIALS", "账号已锁定，请稍后再试")

        if not security.verify_password(credential.password_hash, password):
            credential.failed_attempts += 1
            if credential.failed_attempts >= 5:
                credential.locked_until = now + timedelta(minutes=15)
                credential.failed_attempts = 0
            await self.session.commit()
            raise AuthError("AUTH_INVALID_CREDENTIALS", "账号或密码错误")

        credential.failed_attempts = 0
        credential.locked_until = None
        access_token = security.create_access_token(
            sub=str(user.id), tenant=str(user.tenant_id), scopes=["self"]
        )
        refresh_token = security.generate_refresh_token()
        await self._create_session(user.id, refresh_token)
        await self.session.commit()
        return access_token, refresh_token, user

    async def refresh(self, refresh_token: str) -> tuple[str, str, User]:
        session_row = await self._find_session(refresh_token)
        if session_row is None:
            raise AuthError("AUTH_SESSION_REVOKED", "会话无效")

        now = datetime.now(timezone.utc)
        if session_row.revoked_at is not None:
            await self._revoke_user_sessions(session_row.user_id)
            await self.session.commit()
            raise AuthError("AUTH_SESSION_REVOKED", "检测到刷新令牌复用")

        if session_row.expires_at is None or session_row.expires_at < now:
            raise AuthError("AUTH_SESSION_REVOKED", "会话已过期")

        user = await self.session.get(User, session_row.user_id)
        if user is None or not user.is_active:
            raise AuthError("AUTH_SESSION_REVOKED", "用户不可用")

        new_refresh_token = security.generate_refresh_token()
        new_session = await self._create_session(user.id, new_refresh_token)
        await self.session.flush()
        session_row.revoked_at = now
        session_row.replaced_by = new_session.id
        access_token = security.create_access_token(
            sub=str(user.id), tenant=str(user.tenant_id), scopes=["self"]
        )
        await self.session.commit()
        return access_token, new_refresh_token, user

    async def logout(self, refresh_token: str) -> None:
        session_row = await self._find_session(refresh_token)
        if session_row is not None and session_row.revoked_at is None:
            session_row.revoked_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def _find_user(self, email: str, tenant_slug: str | None) -> User | None:
        query = select(User).where(User.email == email)
        if tenant_slug is not None:
            query = query.join(Tenant, Tenant.id == User.tenant_id).where(
                Tenant.slug == tenant_slug
            )
        users = (await self.session.execute(query)).scalars().all()
        return users[0] if len(users) == 1 else None

    async def _find_session(self, refresh_token: str) -> Session | None:
        hashed = security.hash_refresh_token(refresh_token)
        return (
            await self.session.execute(select(Session).where(Session.refresh_token_hash == hashed))
        ).scalar_one_or_none()

    async def _create_session(self, user_id: uuid.UUID, refresh_token: str) -> Session:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        session = Session(
            user_id=user_id,
            refresh_token_hash=security.hash_refresh_token(refresh_token),
            issued_at=now,
            expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
        )
        self.session.add(session)
        return session

    async def _revoke_user_sessions(self, user_id: uuid.UUID) -> None:
        query = select(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
        sessions = (await self.session.execute(query)).scalars().all()
        now = datetime.now(timezone.utc)
        for session in sessions:
            session.revoked_at = now
