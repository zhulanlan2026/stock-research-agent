from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import cast

from stock_research.market.store import MarketBarStore, MarketNewsStore
from stock_research.stores.session import session_factory


async def main() -> None:
    symbol = "600519.SH"
    start = datetime(2025, 10, 30, tzinfo=timezone.utc)
    end = datetime(2026, 9, 12, tzinfo=timezone.utc)
    price = 1431.9

    async with session_factory() as session:
        bar_store = MarketBarStore(session)
        news_store = MarketNewsStore(session)

        current = start
        index = 0
        while current.date() <= end.date():
            drift = 2.0 * math.sin(index / 18.0) + 1.2 * math.sin(index / 7.0)
            close = round(price + drift, 2)
            open_price = round(price + 0.4 * math.cos(index / 11.0), 2)
            high = round(max(open_price, close) + 3.5, 2)
            low = round(min(open_price, close) - 3.5, 2)
            volume = 28000 + index % 17 * 1200
            amount = volume * close

            await bar_store.upsert_from_inbox(
                source_event_id=f"demo-bar-{symbol}-{current.date().isoformat()}",
                symbol=symbol,
                period="1d",
                bar_time=current,
                open_price=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                amount=amount,
            )
            price = close
            current += timedelta(days=1)
            index += 1

        news_items = [
            {
                "source_event_id": f"demo-news-{symbol}-001",
                "kind": "announcement",
                "event_time": datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc),
                "headline": "贵州茅台发布2026年半年度经营情况公告",
                "url": "https://example.com/announcements/600519/001",
            },
            {
                "source_event_id": f"demo-news-{symbol}-002",
                "kind": "news",
                "event_time": datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc),
                "headline": "贵州茅台渠道改革持续推进，直营占比提升",
                "url": "https://example.com/news/600519/002",
            },
            {
                "source_event_id": f"demo-news-{symbol}-003",
                "kind": "announcement",
                "event_time": datetime(2026, 9, 10, 8, 30, tzinfo=timezone.utc),
                "headline": "贵州茅台召开2026年第一次临时股东大会",
                "url": "https://example.com/announcements/600519/003",
            },
        ]

        for item in news_items:
            await news_store.upsert_from_inbox(
                source_event_id=cast(str, item["source_event_id"]),
                symbol=symbol,
                kind=cast(str, item["kind"]),
                event_time=cast(datetime, item["event_time"]),
                headline=cast(str, item["headline"]),
                url=cast(str, item["url"]),
                payload={"symbol": symbol, "headline": cast(str, item["headline"])},
            )

        await session.commit()
        print(
            f"seeded demo market bars and news for {symbol} "
            f"from {start.date()} to {end.date()}"
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
