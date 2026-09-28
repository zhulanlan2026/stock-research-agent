from datetime import datetime, timedelta, timezone

import pytest

from stock_research.quant.backtest import run_moving_average_backtest


def _closes(count: int) -> tuple[list[datetime], list[float]]:
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    times = [start + timedelta(days=index) for index in range(count)]
    closes = [100.0 + index for index in range(count)]
    return times, closes


def test_moving_average_backtest_returns_metrics() -> None:
    times, closes = _closes(150)

    result = run_moving_average_backtest(
        "603893.SH",
        times,
        closes,
        short_window=20,
        long_window=60,
    )

    assert result.bars == 150
    assert result.strategy == "moving_average"
    assert result.buy_hold_return > 0
    assert result.strategy_return >= 0
    assert result.max_drawdown >= 0
    assert len(result.curve) == 150


def test_moving_average_backtest_rejects_invalid_windows() -> None:
    times, closes = _closes(100)

    with pytest.raises(ValueError):
        run_moving_average_backtest(
            "603893.SH",
            times,
            closes,
            short_window=60,
            long_window=20,
        )


def test_moving_average_backtest_requires_enough_bars() -> None:
    times, closes = _closes(10)

    with pytest.raises(ValueError):
        run_moving_average_backtest(
            "603893.SH",
            times,
            closes,
            short_window=20,
            long_window=60,
        )
