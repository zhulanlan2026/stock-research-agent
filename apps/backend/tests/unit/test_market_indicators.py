from datetime import datetime, timedelta, timezone
from typing import Any

from stock_research.market.indicators import IndicatorService
from stock_research.stores.models.market import MarketBar


async def test_indicators_compute_ma_and_ema(db_context: Any) -> None:
    async with db_context.factory() as session:
        for index in range(5):
            session.add(
                MarketBar(
                    symbol="600519.SH",
                    period="1m",
                    bar_time=datetime(2026, 8, 23, 1, index, 0, tzinfo=timezone.utc),
                    open=float(index),
                    high=float(index + 1),
                    low=float(index),
                    close=float(index + 1),
                    volume=float(index + 1),
                    amount=float((index + 1) * 10),
                    source_event_id=f"bar-{index}",
                )
            )
        await session.commit()

        points = await IndicatorService(session).indicators("600519.SH", "1m", 100)

        assert len(points) == 5
        assert points[4].ma5 == 3.0
        assert points[4].ema5 is not None
        assert points[4].volume_ma5 == 3.0


async def test_indicators_compute_macd_and_rsi(db_context: Any) -> None:
    async with db_context.factory() as session:
        for index in range(30):
            session.add(
                MarketBar(
                    symbol="600519.SH",
                    period="1d",
                    bar_time=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index),
                    open=float(index),
                    high=float(index + 1),
                    low=float(index),
                    close=float(index + 1),
                    volume=float(index + 1),
                    amount=float((index + 1) * 10),
                    source_event_id=f"macd-bar-{index}",
                )
            )
        await session.commit()

        points = await IndicatorService(session).indicators("600519.SH", "1d", 100)

        assert points[-1].macd_dif is not None
        assert points[-1].macd_dea is not None
        assert points[-1].macd_hist is not None
        assert points[-1].rsi is not None
        assert 0 <= (points[-1].rsi or 0) <= 100
