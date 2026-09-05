from datetime import datetime, timezone
from typing import Any

from stock_research.market.analysis import MarketAnalysisService
from stock_research.market.cache import MarketSnapshotCache
from stock_research.market.consumer import MarketDataConsumer
from stock_research.stores.models.workflow import InboxEvent


class _FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, *, ex: int) -> None:
        self.data[key] = value.encode("utf-8")

    def flush(self) -> None:
        self.data.clear()


async def test_market_snapshot_cache_roundtrip() -> None:
    client: Any = _FakeRedis()
    cache = MarketSnapshotCache(client)

    payload = {"symbol": "600519.SH", "last_price": 10.2, "event_time": "2023-12-22T01:30:00+00:00"}
    await cache.set_summary("600519.SH", payload)

    assert await cache.get_summary("600519.SH") == payload


async def test_market_summary_recovers_after_redis_flush(db_context: Any) -> None:
    async with db_context.factory() as session:
        session.add(
            InboxEvent(
                event_id="evt-recover",
                event_type="market.snapshot",
                payload={
                    "symbol": "600519.SH",
                    "time": 1703228400000,
                    "lastPrice": 9.2,
                },
                received_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
        await MarketDataConsumer(session).consume_pending()

        redis = _FakeRedis()
        service = MarketAnalysisService(session, cache=MarketSnapshotCache(redis))

        first = await service.summarize("600519.SH")
        assert redis.data

        redis.flush()

        second = await service.summarize("600519.SH")
        assert second.last_price == first.last_price
