from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BacktestCurvePoint:
    time: datetime
    equity: float


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    strategy: str
    short_window: int
    long_window: int
    bars: int
    buy_hold_return: float
    strategy_return: float
    annualized_return: float
    max_drawdown: float
    trades: int
    curve: list[BacktestCurvePoint]


def _moving_average(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    running = 0.0
    for index, value in enumerate(values):
        running += value
        if index >= window:
            running -= values[index - window]
        if index >= window - 1:
            out[index] = running / window
    return out


def run_moving_average_backtest(
    symbol: str,
    times: list[datetime],
    closes: list[float],
    *,
    short_window: int = 20,
    long_window: int = 60,
) -> BacktestResult:
    if short_window <= 0 or long_window <= 0 or short_window >= long_window:
        raise ValueError("short_window must be positive and smaller than long_window")
    if len(closes) < long_window + 2:
        raise ValueError("insufficient bars for backtest")

    ma_short = _moving_average(closes, short_window)
    ma_long = _moving_average(closes, long_window)

    position = 0
    trades = 0
    strategy: list[int] = []
    for index in range(len(closes)):
        short_value = ma_short[index]
        long_value = ma_long[index]
        if short_value is not None and long_value is not None:
            signal = 1 if short_value > long_value else 0
            if signal != position:
                trades += 1
            position = signal
        strategy.append(position)

    daily_returns: list[float] = []
    for index in range(1, len(closes)):
        if closes[index - 1] == 0:
            daily_returns.append(0.0)
            continue
        daily_return = closes[index] / closes[index - 1] - 1
        daily_returns.append(daily_return * strategy[index - 1])

    equity = 1.0
    curve: list[BacktestCurvePoint] = [BacktestCurvePoint(time=times[0], equity=1.0)]
    for index, daily_return in enumerate(daily_returns):
        equity *= 1 + daily_return
        curve.append(BacktestCurvePoint(time=times[index + 1], equity=equity))

    buy_hold_return = closes[-1] / closes[0] - 1 if closes[0] != 0 else 0.0
    strategy_return = equity - 1
    years = len(closes) / 252
    annualized_return = equity ** (1 / years) - 1 if years > 0 and equity > 0 else 0.0

    peak = 1.0
    max_drawdown = 0.0
    for point in curve:
        peak = max(peak, point.equity)
        drawdown = (peak - point.equity) / peak if peak > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)

    return BacktestResult(
        symbol=symbol,
        strategy="moving_average",
        short_window=short_window,
        long_window=long_window,
        bars=len(closes),
        buy_hold_return=buy_hold_return,
        strategy_return=strategy_return,
        annualized_return=annualized_return,
        max_drawdown=max_drawdown,
        trades=trades,
        curve=curve,
    )
