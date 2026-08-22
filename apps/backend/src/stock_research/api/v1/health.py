import asyncio

from fastapi import APIRouter, Response, status

from stock_research.core.config import get_settings

router = APIRouter()


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


async def _check_postgres(dsn: str) -> bool:
    try:
        import asyncpg  # type: ignore[import-untyped]

        conn = await asyncpg.connect(dsn.replace("postgresql+asyncpg", "postgresql"))
        try:
            await conn.execute("SELECT 1")
        finally:
            await conn.close()
        return True
    except Exception:
        return False


async def _check_redis(url: str) -> bool:
    try:
        import redis.asyncio as redis

        client = redis.from_url(url, socket_timeout=1)  # type: ignore[no-untyped-call]
        try:
            return bool(await client.ping())
        finally:
            await client.aclose()
    except Exception:
        return False


def _check_minio_sync(endpoint: str, access_key: str, secret_key: str, secure: bool) -> bool:
    try:
        from minio import Minio

        client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        client.list_buckets()
        return True
    except Exception:
        return False


@router.get("/ready")
async def ready(response: Response) -> dict[str, object]:
    settings = get_settings()
    postgres_ok, redis_ok, minio_ok = await asyncio.gather(
        _check_postgres(settings.database_url),
        _check_redis(settings.redis_url),
        asyncio.to_thread(
            _check_minio_sync,
            settings.minio_endpoint,
            settings.minio_access_key,
            settings.minio_secret_key,
            settings.minio_secure,
        ),
    )
    dependencies = {
        "postgresql": "ok" if postgres_ok else "unavailable",
        "redis": "ok" if redis_ok else "unavailable",
        "minio": "ok" if minio_ok else "unavailable",
    }
    ready = postgres_ok and redis_ok and minio_ok
    response.status_code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready else "not_ready", "dependencies": dependencies}
