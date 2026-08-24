import pandas as pd
import pytest

from xtquant_collector.xtquant import XtQuantBarFetcher, normalize_bar, parse_xt_time


def test_normalize_bar_is_deterministic() -> None:
    first = normalize_bar(
        symbol="600519.SH",
        period="1d",
        time_ms=1703228400000,
        open_price=10.0,
        high=10.5,
        low=9.9,
        close=10.2,
        volume=1200.0,
        amount=12000.0,
    )
    second = normalize_bar(
        symbol="600519.SH",
        period="1d",
        time_ms=1703228400000,
        open_price=10.0,
        high=10.5,
        low=9.9,
        close=10.2,
        volume=1200.0,
        amount=12000.0,
    )

    assert first == second
    assert first.event_type == "market.bar"
    assert first.payload["open"] == 10.0


def test_parse_xt_time() -> None:
    assert parse_xt_time("20231222") == 1703203200000
    assert parse_xt_time("20231222113000") == 1703244600000


def test_bar_fetcher_requires_xtquant() -> None:
    with pytest.raises(RuntimeError, match="xtquant is not installed"):
        XtQuantBarFetcher().fetch(["600519.SH"], "1d")


def test_extract_events_parses_symbol_keyed_frame() -> None:
    fetcher = XtQuantBarFetcher()
    frame = pd.DataFrame(
        {
            "open": [1299.80, 1291.50],
            "high": [1306.88, 1291.50],
            "low": [1291.00, 1272.01],
            "close": [1291.50, 1272.83],
            "volume": [25332.0, 33472.0],
            "amount": [3.280474e9, 4.278311e9],
        },
        index=[20260820, 20260821],
    )
    data = {"600519.SH": frame}

    events = fetcher._extract_events(data, ["600519.SH"], "1d")

    assert len(events) == 2
    assert events[0].event_type == "market.bar"
    assert events[0].payload["symbol"] == "600519.SH"
    assert events[0].payload["close"] == 1291.50
    assert events[0].payload["volume"] == 25332.0
    assert events[0].payload["time"] == 1787184000000
