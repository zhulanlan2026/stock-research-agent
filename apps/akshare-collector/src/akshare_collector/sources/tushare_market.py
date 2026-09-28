from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from akshare_collector.sources.records import AnnouncementRecord, BarRecord, QuoteRecord
from akshare_collector.sources.symbols import tushare_code
from akshare_collector.sources.timeutil import date_str, datetime_ms, utcnow_ms

TushareBarsRawFn = Callable[
    [str, str, str, str, str | None], list[dict[str, object]]
]

_PERIOD_TO_FREQ = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "60min",
    "1d": "D",
}


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
    if number != number:
        return None
    return number


def _first(row: dict[str, object], *keys: str) -> object:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None


def _bar_from_row(symbol: str, period: str, row: dict[str, object]) -> BarRecord | None:
    time_ms = datetime_ms(_first(row, "trade_time", "trade_date", "date"))
    open_price = _number(row.get("open"))
    high = _number(row.get("high"))
    low = _number(row.get("low"))
    close = _number(row.get("close"))
    volume = _number(_first(row, "vol", "volume"))
    amount = _number(row.get("amount"))
    if time_ms is None or open_price is None or high is None or low is None or close is None:
        return None
    # Tushare 的 amount 单位为千元，后端契约与 AKShare 保持一致使用元。
    if amount is not None:
        amount *= 1000
    return BarRecord(
        symbol=symbol,
        period=period,
        time_ms=time_ms,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        amount=amount,
    )


def _make_default_bars_raw(token: str) -> TushareBarsRawFn:
    import tushare as ts  # type: ignore[import-untyped]

    def fetch(
        ts_code: str,
        freq: str,
        start_date: str,
        end_date: str,
        adjust: str | None,
    ) -> list[dict[str, object]]:
        pro = ts.pro_api(token)
        frame = ts.pro_bar(
            api=pro,
            ts_code=ts_code,
            freq=freq,
            start_date=start_date,
            end_date=end_date,
            adj=adjust,
        )
        return _records(frame)

    return fetch


class TushareMarketSource:
    """Tushare 行情数据源，用于替代 AKShare 作为主数据源。

    Tushare 不提供免费实时快照与公告，因此快照用最新日线收盘价近似，
    公告仍返回空列表。
    """

    name = "tushare"

    def __init__(
        self,
        token: str,
        *,
        history_days: int = 730,
        adjust: str = "",
        bars_fn: TushareBarsRawFn | None = None,
    ) -> None:
        self.token = token.strip()
        self.history_days = history_days
        self.adjust = adjust.strip().lower()
        self._bars_fn = bars_fn or _make_default_bars_raw(self.token)

    def fetch_bars(
        self,
        symbols: Sequence[str],
        period: str,
        *,
        adjust: str | None = None,
    ) -> list[BarRecord]:
        if not symbols:
            return []
        if not self.token:
            raise ValueError("Tushare token is required to fetch bars")

        freq = _PERIOD_TO_FREQ.get(period)
        if freq is None:
            raise ValueError(f"unsupported period: {period}")

        now = datetime.now(timezone.utc)
        start_date = date_str(now - timedelta(days=self.history_days))
        end_date = date_str(now)
        effective_adjust = (adjust if adjust is not None else self.adjust) or None
        if period != "1d":
            effective_adjust = None

        bars: list[BarRecord] = []
        for symbol in symbols:
            ts_code = tushare_code(symbol)
            for row in self._bars_fn(ts_code, freq, start_date, end_date, effective_adjust):
                bar = _bar_from_row(symbol, period, row)
                if bar is not None:
                    bars.append(bar)
        return bars

    def fetch_quotes(self, symbols: Sequence[str]) -> list[QuoteRecord]:
        if not symbols or not self.token:
            return []
        now = datetime.now(timezone.utc)
        start_date = date_str(now - timedelta(days=7))
        end_date = date_str(now)
        now_ms = utcnow_ms()
        quotes: list[QuoteRecord] = []
        for symbol in symbols:
            ts_code = tushare_code(symbol)
            rows = self._bars_fn(ts_code, "D", start_date, end_date, None)
            if not rows:
                continue
            latest = max(
                rows,
                key=lambda row: str(_first(row, "trade_date", "date") or ""),
            )
            close = _number(latest.get("close"))
            if close is None:
                continue
            quotes.append(
                QuoteRecord(
                    symbol=symbol,
                    time_ms=now_ms,
                    fields={"lastPrice": close},
                )
            )
        return quotes

    def fetch_announcements(
        self,
        symbols: Sequence[str],
        *,
        lookback_days: int = 30,
    ) -> list[AnnouncementRecord]:
        return []
