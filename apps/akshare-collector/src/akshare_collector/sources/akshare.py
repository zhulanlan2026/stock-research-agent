from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from akshare_collector.sources.records import AnnouncementRecord, BarRecord, QuoteRecord
from akshare_collector.sources.symbols import akshare_code
from akshare_collector.sources.timeutil import date_str, datetime_ms, utcnow_ms

BarsRawFn = Callable[[str, str, str, str], list[dict[str, object]]]
SpotRawFn = Callable[[], list[dict[str, object]]]
AnnouncementsRawFn = Callable[[str, str, str], list[dict[str, object]]]

_PERIOD_TO_MINUTE = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "1h": "60"}


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


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bar_from_row(symbol: str, period: str, row: dict[str, object]) -> BarRecord | None:
    time_ms = datetime_ms(_first(row, "日期", "时间", "trade_date", "date"))
    open_price = _number(_first(row, "开盘", "open"))
    high = _number(_first(row, "最高", "high"))
    low = _number(_first(row, "最低", "low"))
    close = _number(_first(row, "收盘", "close"))
    volume = _number(_first(row, "成交量", "volume", "vol"))
    amount = _number(_first(row, "成交额", "amount"))
    if time_ms is None or open_price is None or high is None or low is None or close is None:
        return None
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


def _default_bars_raw(
    symbol: str,
    period: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, object]]:
    import akshare as ak  # type: ignore[import-untyped]

    code = akshare_code(symbol)
    if period == "1d":
        frame = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
    else:
        minute = _PERIOD_TO_MINUTE.get(period)
        if minute is None:
            raise ValueError(f"unsupported period: {period}")
        frame = ak.stock_zh_a_hist_min_em(symbol=code, period=minute, adjust="")
    return _records(frame)


def _default_spot_raw() -> list[dict[str, object]]:
    import akshare as ak

    return _records(ak.stock_zh_a_spot_em())


def _default_announcements_raw(
    symbol: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, object]]:
    import akshare as ak

    frame = ak.stock_zh_a_disclosure_report_cninfo(
        symbol=akshare_code(symbol),
        market="沪深京",
        start_date=start_date,
        end_date=end_date,
    )
    return _records(frame)


def _announcement_from_row(symbol: str, row: dict[str, object]) -> AnnouncementRecord | None:
    headline = _optional_string(_first(row, "公告标题", "公告名称", "title", "headline"))
    if headline is None:
        return None
    url = _optional_string(_first(row, "公告链接", "网址", "url", "link"))
    source = _optional_string(_first(row, "公告来源", "来源", "source"))
    time_ms = datetime_ms(_first(row, "公告时间", "公告日期", "date", "datetime", "published_at"))
    return AnnouncementRecord(
        symbol=symbol,
        time_ms=time_ms if time_ms is not None else utcnow_ms(),
        headline=headline,
        url=url,
        source=source,
    )


class AkShareMarketSource:
    """AKShare 行情数据源，原始接口可注入以便单元测试。"""

    name = "akshare"

    def __init__(
        self,
        *,
        history_days: int = 730,
        bars_fn: BarsRawFn | None = None,
        spot_fn: SpotRawFn | None = None,
        announcements_fn: AnnouncementsRawFn | None = None,
    ) -> None:
        self.history_days = history_days
        self._bars_fn = bars_fn
        self._spot_fn = spot_fn
        self._announcements_fn = announcements_fn

    def fetch_bars(self, symbols: Sequence[str], period: str) -> list[BarRecord]:
        if not symbols:
            return []
        bars_fn = self._bars_fn or _default_bars_raw
        now = datetime.now(timezone.utc)
        start_date = date_str(now - timedelta(days=self.history_days))
        end_date = date_str(now)
        bars: list[BarRecord] = []
        for symbol in symbols:
            for row in bars_fn(symbol, period, start_date, end_date):
                bar = _bar_from_row(symbol, period, row)
                if bar is not None:
                    bars.append(bar)
        return bars

    def fetch_quotes(self, symbols: Sequence[str]) -> list[QuoteRecord]:
        if not symbols:
            return []
        spot_fn = self._spot_fn or _default_spot_raw
        code_to_symbol = {akshare_code(symbol): symbol for symbol in symbols}
        now_ms = utcnow_ms()
        quotes: list[QuoteRecord] = []
        for row in spot_fn():
            code = _optional_string(_first(row, "代码", "code"))
            symbol = code_to_symbol.get(code or "")
            if symbol is None:
                continue
            fields: dict[str, object] = {
                "name": _first(row, "名称", "name"),
                "lastPrice": _number(_first(row, "最新价", "lastPrice", "last_price")),
                "lastClose": _number(_first(row, "昨收", "lastClose", "preClose")),
                "preClose": _number(_first(row, "昨收", "preClose", "lastClose")),
                "open": _number(_first(row, "今开", "open")),
                "high": _number(_first(row, "最高", "high")),
                "low": _number(_first(row, "最低", "low")),
                "volume": _number(_first(row, "成交量", "volume")),
                "amount": _number(_first(row, "成交额", "amount")),
                "change_pct": _number(_first(row, "涨跌幅", "change_pct")),
            }
            quotes.append(QuoteRecord(symbol=symbol, time_ms=now_ms, fields=fields))
        return quotes

    def fetch_announcements(
        self,
        symbols: Sequence[str],
        *,
        lookback_days: int = 30,
    ) -> list[AnnouncementRecord]:
        if not symbols:
            return []
        announcements_fn = self._announcements_fn or _default_announcements_raw
        now = datetime.now(timezone.utc)
        start_date = date_str(now - timedelta(days=lookback_days))
        end_date = date_str(now)
        records: list[AnnouncementRecord] = []
        for symbol in symbols:
            for row in announcements_fn(symbol, start_date, end_date):
                record = _announcement_from_row(symbol, row)
                if record is not None:
                    records.append(record)
        return records
