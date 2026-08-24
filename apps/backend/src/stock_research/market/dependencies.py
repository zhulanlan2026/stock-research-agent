from collections.abc import AsyncIterator

from fastapi import Depends

from stock_research.core.config import Settings, get_settings
from stock_research.market.cache import MarketSnapshotCache


async def get_market_snapshot_cache(
    settings: Settings = Depends(get_settings),
) -> AsyncIterator[MarketSnapshotCache | None]:
    try:
        import redis.asyncio as redis

        client = redis.from_url(  # type: ignore[no-untyped-call]
            settings.redis_url,
            socket_timeout=1,
            decode_responses=False,
        )
    except Exception:
        yield None
        return

    cache = MarketSnapshotCache(client)
    try:
        yield cache
    finally:
        await client.aclose()
