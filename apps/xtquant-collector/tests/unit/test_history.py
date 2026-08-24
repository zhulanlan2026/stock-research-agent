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
