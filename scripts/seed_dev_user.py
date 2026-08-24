import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from stock_research.auth.security import hash_password
from stock_research.core.config import get_settings
from stock_research.iam.service import PermissionService
from stock_research.stores.models.iam import Credential, Role, Tenant, User, UserRole


async def seed(email: str, password: str, role_code: str, tenant_slug: str) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(name=tenant_slug, slug=tenant_slug, status="active")
            session.add(tenant)
            await session.flush()

        user = (
            await session.execute(
                select(User).where(User.tenant_id == tenant.id, User.email == email)
            )
        ).scalar_one_or_none()
        if user is None:
            user = User(
                tenant_id=tenant.id,
                email=email,
                display_name=email,
                status="active",
                is_active=True,
            )
            session.add(user)
            await session.flush()

        credential = (
            await session.execute(select(Credential).where(Credential.user_id == user.id))
        ).scalar_one_or_none()
        if credential is None:
            session.add(Credential(user_id=user.id, password_hash=hash_password(password)))
        else:
            # 已存在则覆盖密码并清空锁定状态，保证 seed 幂等且密码与参数一致。
            credential.password_hash = hash_password(password)
            credential.failed_attempts = 0
            credential.locked_until = None

        role = (
            await session.execute(
                select(Role).where(Role.tenant_id == tenant.id, Role.code == role_code)
            )
        ).scalar_one_or_none()
        if role is None:
            role = Role(
                tenant_id=tenant.id,
                code=role_code,
                name=role_code,
                is_system=(role_code == "ADMIN"),
            )
            session.add(role)
            await session.flush()
        await PermissionService(session).ensure_role_permissions(role, role_code)

        user_role = (
            await session.execute(
                select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
            )
        ).scalar_one_or_none()
        if user_role is None:
            session.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=tenant.id))

        await session.commit()

    await engine.dispose()
    print(f"seeded user {email} in tenant {tenant_slug} with role {role_code}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a local development user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", default="ADMIN")
    parser.add_argument("--tenant-slug", default="dev")
    args = parser.parse_args()

    asyncio.run(seed(args.email, args.password, args.role, args.tenant_slug))


if __name__ == "__main__":
    main()
