from datetime import datetime, timezone

from stock_research.market.gap import BarGapDetector
from stock_research.stores.models.market import MarketBar


def _bar(bar_time: datetime) -> MarketBar:
    return MarketBar(
        symbol="600519.SH",
        period="1m",
        bar_time=bar_time,
        open=1.0,
        high=1.0,
        low=1.0,
        close=1.0,
        source_event_id=f"evt-{bar_time.timestamp()}",
    )


def test_bar_gap_detector_returns_missing_intraday_bars() -> None:
    start = datetime(2023, 12, 22, 1, 30, tzinfo=timezone.utc)
    bars = [_bar(start), _bar(start.replace(minute=32))]

    missing = BarGapDetector().missing_times(bars, "1m")

    assert missing == [start.replace(minute=31)]


def test_bar_gap_detector_returns_empty_when_complete() -> None:
    start = datetime(2023, 12, 22, 1, 30, tzinfo=timezone.utc)
    bars = [_bar(start), _bar(start.replace(minute=31)), _bar(start.replace(minute=32))]

    assert BarGapDetector().missing_times(bars, "1m") == []
