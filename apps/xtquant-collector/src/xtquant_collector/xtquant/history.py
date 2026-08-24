from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class BarEvent:
    event_id: str
    event_type: str
    payload: dict[str, object]


def normalize_bar(
    *,
    symbol: str,
    period: str,
    time_ms: int,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float | None,
    amount: float | None,
) -> BarEvent:
    payload: dict[str, object] = {
        "symbol": symbol,
        "period": period,
        "time": time_ms,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "amount": amount,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    event_id = "bar:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return BarEvent(event_id=event_id, event_type="market.bar", payload=payload)


def parse_xt_time(value: str) -> int:
    """将 XTQuant 的 '20231222' 或 '20231222113000' 时间标签转为毫秒时间戳。"""
    formats = {8: "%Y%m%d", 14: "%Y%m%d%H%M%S"}
    fmt = formats.get(len(value))
    if fmt is None:
        raise ValueError(f"unsupported XTQuant time label: {value}")
    parsed = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


class XtQuantBarFetcher:
    """通过 XTQuant 历史行情接口获取标准 K 线。"""

    def fetch(
        self,
        symbols: Sequence[str],
        period: str,
        count: int = 300,
    ) -> list[BarEvent]:
        if not symbols:
            return []

        try:
            from xtquant import xtdata  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "xtquant is not installed; run the collector on Windows MiniQMT"
            ) from exc

        for symbol in symbols:
            xtdata.download_history_data(
                str(symbol),
                period=period,
                start_time="",
                end_time="",
            )

        data = xtdata.get_market_data_ex(
            field_list=["open", "high", "low", "close", "volume", "amount"],
            stock_list=list(symbols),
            period=period,
            start_time="",
            end_time="",
            count=count,
            dividend_type="none",
            fill_data=True,
        )
        return self._extract_events(data, list(symbols), period)

    def _extract_events(
        self,
        data: dict[str, Any],
        symbols: Sequence[str],
        period: str,
    ) -> list[BarEvent]:
        if not data or not symbols:
            return []

        events: list[BarEvent] = []
        open_frame = data.get("open")
        if open_frame is None:
            return events

        for symbol in symbols:
            try:
                open_series = open_frame.loc[symbol]
            except Exception:
                continue

            for time_label in open_series.index:
                try:
                    time_ms = parse_xt_time(str(time_label))
                    open_price = float(open_series[time_label])
                    high = float(data["high"].loc[symbol][time_label])
                    low = float(data["low"].loc[symbol][time_label])
                    close = float(data["close"].loc[symbol][time_label])
                    if not all(
                        math.isfinite(value)
                        for value in (open_price, high, low, close)
                    ):
                        continue
                    volume_value = data.get("volume")
                    amount_value = data.get("amount")
                    volume = (
                        _nullable_float(volume_value.loc[symbol][time_label])
                        if volume_value is not None
                        else None
                    )
                    amount = (
                        _nullable_float(amount_value.loc[symbol][time_label])
                        if amount_value is not None
                        else None
                    )
                except Exception:
                    continue

                events.append(
                    normalize_bar(
                        symbol=str(symbol),
                        period=period,
                        time_ms=time_ms,
                        open_price=open_price,
                        high=high,
                        low=low,
                        close=close,
                        volume=volume,
                        amount=amount,
                    )
                )

        return events


def _nullable_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None
