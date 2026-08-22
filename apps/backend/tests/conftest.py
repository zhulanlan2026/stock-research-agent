import asyncio
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path

import asyncpg  # type: ignore[import-untyped]
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from stock_research.auth.security import hash_password
from stock_research.core.config import get_settings
from stock_research.stores.models.iam import Credential, Role, Tenant, User, UserRole

BACKEND_DIR = Path(__file__).resolve().parents[1]


@dataclass
class TestDbContext:
    factory: async_sessionmaker[AsyncSession]
    override: Callable[[], AsyncIterator[AsyncSession]]
    email: str
    password: str
    free_email: str
    free_password: str
    tenant_id: uuid.UUID
    user_id: uuid.UUID


def _replace_database(dsn: str, database: str) -> str:
    base = dsn.replace("localhost", "127.0.0.1")
    return f"{base.rsplit('/', 1)[0]}/{database}"


def _asyncpg_dsn(dsn: str) -> str:
    return dsn.replace("postgresql+asyncpg", "postgresql")


async def _create_database(database: str) -> None:
    admin_dsn = _asyncpg_dsn(_replace_database(get_settings().database_url, "postgres"))
    conn = await asyncpg.connect(admin_dsn, timeout=2)
    try:
        await conn.execute(f'CREATE DATABASE "{database}"')
    finally:
        await conn.close()


async def _drop_database(database: str) -> None:
    admin_dsn = _asyncpg_dsn(_replace_database(get_settings().database_url, "postgres"))
    conn = await asyncpg.connect(admin_dsn, timeout=2)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
    finally:
        await conn.close()


@pytest.fixture
async def db_context() -> AsyncIterator[TestDbContext]:
    database = f"stock_research_test_{uuid.uuid4().hex[:8]}"
    try:
        await _create_database(database)
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"PostgreSQL unavailable: {exc}")

    settings = get_settings()
    dsn = _replace_database(settings.database_url, database)

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", dsn)
    await asyncio.to_thread(command.upgrade, config, "head")

    engine = create_async_engine(dsn)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    email = "test@example.com"
    password = "correct-horse-battery"
    free_email = "free@example.com"
    free_password = "free-user-password"

    async with factory() as session:
        tenant = Tenant(name="dev", slug="dev", status="active")
        session.add(tenant)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            email=email,
            display_name=email,
            status="active",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        session.add(Credential(user_id=user.id, password_hash=hash_password(password)))
        role = Role(tenant_id=tenant.id, code="ADMIN", name="ADMIN", is_system=True)
        session.add(role)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=tenant.id))

        free_user = User(
            tenant_id=tenant.id,
            email=free_email,
            display_name=free_email,
            status="active",
            is_active=True,
        )
        session.add(free_user)
        await session.flush()
        session.add(Credential(user_id=free_user.id, password_hash=hash_password(free_password)))
        free_role = Role(tenant_id=tenant.id, code="FREE_USER", name="FREE_USER", is_system=False)
        session.add(free_role)
        await session.flush()
        session.add(UserRole(user_id=free_user.id, role_id=free_role.id, tenant_id=tenant.id))
        await session.commit()

        tenant_id = tenant.id
        user_id = user.id

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    yield TestDbContext(
        factory=factory,
        override=override_get_session,
        email=email,
        password=password,
        free_email=free_email,
        free_password=free_password,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    await engine.dispose()
    await _drop_database(database)
