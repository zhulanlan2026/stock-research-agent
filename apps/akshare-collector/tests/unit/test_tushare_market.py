import pytest

from akshare_collector.sources.tushare_market import TushareMarketSource


def test_fetch_bars_maps_daily_columns_and_converts_amount() -> None:
    def bars_fn(
        ts_code: str,
        freq: str,
        start_date: str,
        end_date: str,
        adjust: str | None,
    ) -> list[dict[str, object]]:
        assert ts_code == "600519.SH"
        assert freq == "D"
        return [
            {
                "trade_date": "20250102",
                "open": 1700.0,
                "high": 1710.0,
                "low": 1690.0,
                "close": 1705.0,
                "vol": 1000.0,
                "amount": 170500.0,
            }
        ]

    source = TushareMarketSource("token", history_days=365, bars_fn=bars_fn)

    bars = source.fetch_bars(["600519.SH"], "1d")

    assert len(bars) == 1
    assert bars[0].symbol == "600519.SH"
    assert bars[0].period == "1d"
    assert bars[0].close == 1705.0
    assert bars[0].volume == 1000.0
    assert bars[0].amount == 170500000.0


def test_fetch_bars_maps_minute_trade_time() -> None:
    def bars_fn(
        ts_code: str,
        freq: str,
        start_date: str,
        end_date: str,
        adjust: str | None,
    ) -> list[dict[str, object]]:
        assert freq == "5min"
        return [
            {
                "trade_time": "2025-01-02 10:05:00",
                "open": 1700.0,
                "high": 1701.0,
                "low": 1699.0,
                "close": 1700.5,
                "vol": 120.0,
                "amount": 20000.0,
            }
        ]

    source = TushareMarketSource("token", history_days=365, bars_fn=bars_fn)

    bars = source.fetch_bars(["600519.SH"], "5m")

    assert len(bars) == 1
    assert bars[0].period == "5m"
    assert bars[0].time_ms > 0
    assert bars[0].close == 1700.5


def test_fetch_bars_uses_adjust_for_daily_only() -> None:
    seen: list[str | None] = []

    def bars_fn(
        ts_code: str,
        freq: str,
        start_date: str,
        end_date: str,
        adjust: str | None,
    ) -> list[dict[str, object]]:
        seen.append(adjust)
        return []

    source = TushareMarketSource("token", adjust="qfq", bars_fn=bars_fn)

    source.fetch_bars(["600519.SH"], "1d")
    source.fetch_bars(["600519.SH"], "1m")

    assert seen == ["qfq", None]


def test_fetch_bars_requires_token() -> None:
    source = TushareMarketSource("", bars_fn=lambda *_: [])

    with pytest.raises(ValueError, match="token"):
        source.fetch_bars(["600519.SH"], "1d")


def test_fetch_bars_rejects_unsupported_period() -> None:
    source = TushareMarketSource("token", bars_fn=lambda *_: [])

    with pytest.raises(ValueError, match="unsupported period"):
        source.fetch_bars(["600519.SH"], "2h")


def test_quotes_and_announcements_are_empty() -> None:
    source = TushareMarketSource("token")

    assert source.fetch_quotes(["600519.SH"]) == []
    assert source.fetch_announcements(["600519.SH"]) == []
