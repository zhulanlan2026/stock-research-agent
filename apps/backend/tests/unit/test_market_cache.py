from typing import Any

from stock_research.market.cache import MarketSnapshotCache


class _FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, *, ex: int) -> None:
        self.data[key] = value.encode("utf-8")


async def test_market_snapshot_cache_roundtrip() -> None:
    client: Any = _FakeRedis()
    cache = MarketSnapshotCache(client)

    payload = {"symbol": "600519.SH", "last_price": 10.2, "event_time": "2023-12-22T01:30:00+00:00"}
    await cache.set_summary("600519.SH", payload)

    assert await cache.get_summary("600519.SH") == payload
