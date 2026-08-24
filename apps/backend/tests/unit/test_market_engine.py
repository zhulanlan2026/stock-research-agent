from datetime import datetime, timezone
from typing import Any

from stock_research.market.engine import MarketEngine, TechnicalEngine
from stock_research.stores.models.workflow import InboxEvent


async def test_technical_engine_is_deterministic(db_context: Any) -> None:
    async with db_context.factory() as session:
        session.add_all(
            [
                InboxEvent(
                    event_id="bar-engine-1",
                    event_type="market.bar",
                    payload={
                        "symbol": "600519.SH",
                        "period": "1d",
                        "time": 1703228400000,
                        "open": 10.0,
                        "high": 11.0,
                        "low": 9.0,
                        "close": 10.5,
                    },
                    received_at=datetime.now(timezone.utc),
                ),
                InboxEvent(
                    event_id="bar-engine-2",
                    event_type="market.bar",
                    payload={
                        "symbol": "600519.SH",
                        "period": "1d",
                        "time": 1703314800000,
                        "open": 10.5,
                        "high": 11.5,
                        "low": 10.0,
                        "close": 11.0,
                    },
                    received_at=datetime.now(timezone.utc),
                ),
            ]
        )
        await session.commit()

        from stock_research.market.consumer import MarketDataConsumer

        await MarketDataConsumer(session).consume_pending()

        first = await TechnicalEngine(session).calculate("600519.SH", "1d", limit=10)
        second = await TechnicalEngine(session).calculate("600519.SH", "1d", limit=10)

        assert first.module_version == "technical:1.0.0"
        assert first.points == second.points


async def test_market_engine_returns_versioned_summary(db_context: Any) -> None:
    async with db_context.factory() as session:
        session.add(
            InboxEvent(
                event_id="snap-engine-1",
                event_type="market.snapshot",
                payload={
                    "symbol": "600519.SH",
                    "time": 1703228400000,
                    "lastPrice": 10.2,
                    "lastClose": 10.0,
                    "bidPrice": [10.1],
                    "askPrice": [10.3],
                },
                received_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        from stock_research.market.consumer import MarketDataConsumer

        await MarketDataConsumer(session).consume_pending()
        result = await MarketEngine(session).calculate("600519.SH")

        assert result.module_version == "market:1.0.0"
        assert result.summary.last_price == 10.2
