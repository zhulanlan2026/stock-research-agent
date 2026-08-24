from datetime import datetime, timezone

from stock_research.market.analysis import summarize_snapshots
from stock_research.stores.models.market import MarketSnapshot


def test_summarize_snapshots_calculates_change_and_spread() -> None:
    event_time = datetime(2026, 8, 23, 1, 0, 0, tzinfo=timezone.utc)
    snapshots = [
        MarketSnapshot(
            symbol="600519.SH",
            source_event_id="evt-1",
            event_time=event_time,
            payload={
                "lastPrice": 10.5,
                "lastClose": 10.0,
                "bidPrice": [10.4, 10.3],
                "askPrice": [10.6, 10.7],
            },
        )
    ]

    summary = summarize_snapshots("600519.SH", snapshots)

    assert summary.last_price == 10.5
    assert summary.previous_close == 10.0
    assert summary.change == 0.5
    assert summary.change_pct == 5.0
    assert summary.bid_ask_spread == 0.2
    assert summary.sample_count == 1


def test_summarize_snapshots_handles_empty() -> None:
    summary = summarize_snapshots("600519.SH", [])

    assert summary.last_price is None
    assert summary.sample_count == 0
