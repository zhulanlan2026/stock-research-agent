from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from stock_research.stores.models.market import MarketBar

_MINUTE_PERIODS = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
}


class BarGapDetector:
    """基于已入库 bar 的时间序列，确定性地发现缺口。"""

    def missing_times(self, bars: Sequence[MarketBar], period: str) -> list[datetime]:
        if len(bars) < 2:
            return []

        actual = {bar.bar_time for bar in bars}
        start = min(actual)
        end = max(actual)
        expected = self._expected_times(start, end, period)
        return [value for value in expected if value not in actual]

    def _expected_times(
        self,
        start: datetime,
        end: datetime,
        period: str,
    ) -> list[datetime]:
        if period in _MINUTE_PERIODS:
            return _intraday_expected(start, end, _MINUTE_PERIODS[period])
        if period == "1d":
            return _daily_expected(start, end)
        raise ValueError(f"unsupported gap detection period: {period}")


def _intraday_expected(
    start: datetime,
    end: datetime,
    step: timedelta,
) -> list[datetime]:
    result: list[datetime] = []
    current = start
    while current <= end:
        result.append(current)
        current += step
    return result


def _daily_expected(start: datetime, end: datetime) -> list[datetime]:
    result: list[datetime] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            result.append(current)
        current += timedelta(days=1)
    return result
