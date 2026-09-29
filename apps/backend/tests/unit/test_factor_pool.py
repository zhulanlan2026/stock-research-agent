from datetime import datetime, timezone
from decimal import Decimal

from stock_research.quant.factor_pool import (
    compute_technical_factors,
    month_end_timestamps,
)


def test_compute_technical_factors_returns_values() -> None:
    closes = [Decimal(str(100 + index)) for index in range(80)]

    factors = compute_technical_factors(closes)

    assert factors["momentum_20"] is not None
    assert factors["momentum_60"] is not None
    assert factors["volatility_20"] is not None
    assert factors["rsi_14"] == Decimal("100")  # 连续上涨，RSI 为 100


def test_compute_technical_factors_none_with_short_history() -> None:
    closes = [Decimal("100"), Decimal("101"), Decimal("102")]

    factors = compute_technical_factors(closes)

    assert factors["momentum_20"] is None
    assert factors["momentum_60"] is None
    assert factors["volatility_20"] is None
    assert factors["rsi_14"] is None


def test_month_end_timestamps() -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 3, 31, tzinfo=timezone.utc)

    timestamps = month_end_timestamps(start, end)

    assert [ts.day for ts in timestamps] == [31, 29, 31]
