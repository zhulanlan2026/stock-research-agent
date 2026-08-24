from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.market.store import MarketBarStore


@dataclass(frozen=True)
class IndicatorPoint:
    time: datetime
    ma5: float | None
    ma10: float | None
    ma20: float | None
    ema5: float | None
    ema10: float | None
    ema20: float | None
    volume_ma5: float | None
    volume_ma10: float | None
    macd_dif: float | None
    macd_dea: float | None
    macd_hist: float | None
    rsi: float | None


class IndicatorService:
    def __init__(self, session: AsyncSession) -> None:
        self.store = MarketBarStore(session)

    async def indicators(
        self,
        symbol: str,
        period: str = "1m",
        limit: int = 100,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
    ) -> list[IndicatorPoint]:
        bars = await self.store.latest(symbol, period, limit)
        closes = [bar.close for bar in bars]
        volumes = [bar.volume for bar in bars]

        ma5 = _sma(closes, 5)
        ma10 = _sma(closes, 10)
        ma20 = _sma(closes, 20)
        ema5 = _ema(closes, 5)
        ema10 = _ema(closes, 10)
        ema20 = _ema(closes, 20)
        volume_ma5 = _sma(volumes, 5)
        volume_ma10 = _sma(volumes, 10)
        macd_dif, macd_dea, macd_hist = _macd(
            closes,
            fast=macd_fast,
            slow=macd_slow,
            signal=macd_signal,
        )
        rsi = _rsi(closes, rsi_period)

        return [
            IndicatorPoint(
                time=bar.bar_time,
                ma5=_round(ma5[index]),
                ma10=_round(ma10[index]),
                ma20=_round(ma20[index]),
                ema5=_round(ema5[index]),
                ema10=_round(ema10[index]),
                ema20=_round(ema20[index]),
                volume_ma5=_round(volume_ma5[index]),
                volume_ma10=_round(volume_ma10[index]),
                macd_dif=_round(macd_dif[index]),
                macd_dea=_round(macd_dea[index]),
                macd_hist=_round(macd_hist[index]),
                rsi=_round(rsi[index]),
            )
            for index, bar in enumerate(bars)
        ]


def _sma(values: Sequence[float | None], period: int) -> list[float | None]:
    result: list[float | None] = []
    window: list[float] = []
    for value in values:
        window.append(value if value is not None else 0.0)
        if len(window) > period:
            window.pop(0)
        result.append(sum(window) / period if len(window) == period else None)
    return result


def _ema(values: Sequence[float | None], period: int) -> list[float | None]:
    alpha = 2 / (period + 1)
    result: list[float | None] = []
    current: float | None = None
    for value in values:
        if value is None:
            result.append(None)
            continue
        if current is None:
            current = value
        else:
            current = alpha * value + (1 - alpha) * current
        result.append(current)
    return result


def _macd(
    values: Sequence[float | None],
    *,
    fast: int,
    slow: int,
    signal: int,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    ema_fast = _ema(values, fast)
    ema_slow = _ema(values, slow)
    dif: list[float | None] = []
    for fast_value, slow_value in zip(ema_fast, ema_slow, strict=True):
        if fast_value is None or slow_value is None:
            dif.append(None)
        else:
            dif.append(fast_value - slow_value)

    dea = _ema(dif, signal)
    hist: list[float | None] = []
    for dif_value, dea_value in zip(dif, dea, strict=True):
        if dif_value is None or dea_value is None:
            hist.append(None)
        else:
            hist.append((dif_value - dea_value) * 2)
    return dif, dea, hist


def _rsi(values: Sequence[float | None], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    clean = [value for value in values if value is not None]
    if len(clean) <= period:
        return result

    avg_gain = 0.0
    avg_loss = 0.0
    for index in range(1, period + 1):
        change = clean[index] - clean[index - 1]
        if change >= 0:
            avg_gain += change
        else:
            avg_loss += -change
    avg_gain /= period
    avg_loss /= period
    result[period] = _rsi_value(avg_gain, avg_loss)

    for index in range(period + 1, len(clean)):
        change = clean[index] - clean[index - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        result[index] = _rsi_value(avg_gain, avg_loss)

    return result


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)
