from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import Any

from akshare_collector.sources.records import BarRecord
from akshare_collector.sources.symbols import tushare_code
from akshare_collector.sources.timeutil import date_str

DailyRawFn = Callable[[str, str, str], list[dict[str, object]]]


def _records(frame: Any) -> list[dict[str, object]]:
    if frame is None:
        return []
    to_dict = getattr(frame, "to_dict", None)
    if not callable(to_dict):
        return []
    records = to_dict(orient="records")
    if not isinstance(records, list):
        return []
    return [dict(record) for record in records if isinstance(record, dict)]


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _default_daily_raw(
    token: str,
    ts_code: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, object]]:
    import tushare as ts  # type: ignore[import-untyped]

    pro = ts.pro_api(token)
    return _records(pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date))


def _bar_date(bar: BarRecord) -> str:
    value = datetime.fromtimestamp(bar.time_ms / 1000, tz=timezone.utc)
    return date_str(value)


def _close_matches(actual: float, expected: float, tolerance: float) -> bool:
    if expected == 0:
        return abs(actual - expected) <= tolerance
    return abs(actual - expected) / abs(expected) <= tolerance


class TushareCrossValidator:
    """用 Tushare 日线对 AKShare 日线做交叉验证。"""

    def __init__(
        self,
        token: str,
        tolerance: float = 0.005,
        *,
        daily_fn: DailyRawFn | None = None,
    ) -> None:
        self.token = token.strip()
        self.tolerance = tolerance
        self._daily_fn = daily_fn

    def validate(self, symbol: str, bars: Sequence[BarRecord]) -> list[str]:
        if not self.token:
            return []
        daily_bars = [bar for bar in bars if bar.period == "1d"]
        if not daily_bars:
            return []

        timestamps = [bar.time_ms for bar in daily_bars]
        start = date_str(datetime.fromtimestamp(min(timestamps) / 1000, tz=timezone.utc))
        end = date_str(datetime.fromtimestamp(max(timestamps) / 1000, tz=timezone.utc))

        ts_code = tushare_code(symbol)
        if self._daily_fn is not None:
            raw = self._daily_fn(ts_code, start, end)
        else:
            raw = _default_daily_raw(self.token, ts_code, start, end)

        expected = {_bar_date(bar): bar for bar in daily_bars}
        mismatches: list[str] = []
        for row in raw:
            trade_date = str(row.get("trade_date") or "").strip()
            bar = expected.get(trade_date)
            if bar is None:
                continue
            tushare_close = _number(row.get("close"))
            if tushare_close is None:
                continue
            if not _close_matches(bar.close, tushare_close, self.tolerance):
                mismatches.append(
                    f"{symbol} {trade_date} close mismatch: "
                    f"akshare={bar.close}, tushare={tushare_close}"
                )
        return mismatches
