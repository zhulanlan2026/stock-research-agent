from akshare_collector.sources.akshare import AkShareMarketSource


def _bars_fn(
    symbol: str,
    period: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, object]]:
    return [
        {
            "日期": "2025-01-02",
            "开盘": 1700.0,
            "最高": 1710.0,
            "最低": 1690.0,
            "收盘": 1705.0,
            "成交量": 1000.0,
            "成交额": 170500000.0,
        }
    ]


def test_fetch_bars_maps_akshare_columns() -> None:
    source = AkShareMarketSource(history_days=365, bars_fn=_bars_fn)

    bars = source.fetch_bars(["600519.SH"], "1d")

    assert len(bars) == 1
    assert bars[0].symbol == "600519.SH"
    assert bars[0].period == "1d"
    assert bars[0].close == 1705.0


def test_fetch_bars_skips_incomplete_rows() -> None:
    def bars_fn(
        symbol: str,
        period: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        return [{"日期": "2025-01-02", "开盘": 1700.0}]

    source = AkShareMarketSource(history_days=365, bars_fn=bars_fn)

    assert source.fetch_bars(["600519.SH"], "1d") == []


def test_fetch_quotes_filters_and_maps_symbols() -> None:
    def spot_fn() -> list[dict[str, object]]:
        return [
            {
                "代码": "600519",
                "名称": "贵州茅台",
                "最新价": 1705.0,
                "昨收": 1700.0,
                "今开": 1701.0,
                "最高": 1710.0,
                "最低": 1690.0,
                "成交量": 1000.0,
                "成交额": 170500000.0,
                "涨跌幅": 0.29,
            },
            {"代码": "999999", "最新价": 1.0},
        ]

    source = AkShareMarketSource(spot_fn=spot_fn)

    quotes = source.fetch_quotes(["600519.SH"])

    assert len(quotes) == 1
    assert quotes[0].symbol == "600519.SH"
    assert quotes[0].fields["lastPrice"] == 1705.0
    assert quotes[0].fields["preClose"] == 1700.0


def test_fetch_announcements_maps_columns() -> None:
    def announcements_fn(
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        return [
            {
                "公告标题": "2025 年度报告",
                "公告时间": "2025-03-01 10:00:00",
                "公告链接": "http://example.com/a.pdf",
                "公告来源": "cninfo",
            }
        ]

    source = AkShareMarketSource(announcements_fn=announcements_fn)

    records = source.fetch_announcements(["600519.SH"])

    assert len(records) == 1
    assert records[0].headline == "2025 年度报告"
