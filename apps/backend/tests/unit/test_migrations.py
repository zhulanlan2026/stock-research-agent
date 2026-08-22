import asyncio
import uuid
from pathlib import Path

import asyncpg  # type: ignore[import-untyped]
import pytest
from alembic import command
from alembic.config import Config

from stock_research.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


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


def test_migrations_upgrade_and_downgrade() -> None:
    database = f"stock_research_test_{uuid.uuid4().hex[:8]}"
    try:
        asyncio.run(_create_database(database))
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"PostgreSQL unavailable, migration test skipped: {exc}")

    test_dsn = _replace_database(get_settings().database_url, database)
    config = _alembic_config()
    config.set_main_option("sqlalchemy.url", test_dsn)

    try:
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        asyncio.run(_drop_database(database))
