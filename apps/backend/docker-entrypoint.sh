#!/usr/bin/env sh
set -eu

cd /app/apps/backend

python - <<'PY'
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from stock_research.core.config import get_settings


async def wait_for_database() -> None:
    url = get_settings().database_url
    last_exc: Exception | None = None
    for _ in range(60):
        try:
            engine = create_async_engine(url)
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            finally:
                await engine.dispose()
            return
        except Exception as exc:
            last_exc = exc
            await asyncio.sleep(2)
    raise RuntimeError("database not reachable after waiting") from last_exc


asyncio.run(wait_for_database())
PY

alembic -c alembic.ini upgrade head

exec uvicorn stock_research.main:app --host 0.0.0.0 --port 8000
