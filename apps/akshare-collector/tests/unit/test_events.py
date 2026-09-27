from akshare_collector.events import (
    normalize_announcement,
    normalize_bar,
    normalize_financial_fact,
    normalize_quote,
)
from akshare_collector.sources.records import AnnouncementRecord, BarRecord, QuoteRecord


def test_normalize_bar() -> None:
    event = normalize_bar(
        BarRecord(
            symbol="600519.SH",
            period="1d",
            time_ms=1703228400000,
            open=1700.0,
            high=1710.0,
            low=1690.0,
            close=1705.0,
            volume=1000.0,
            amount=170500000.0,
        )
    )

    assert event.event_type == "market.bar"
    assert event.payload["symbol"] == "600519.SH"
    assert event.payload["close"] == 1705.0


def test_normalize_quote() -> None:
    event = normalize_quote(
        QuoteRecord(
            symbol="600519.SH",
            time_ms=1703228400000,
            fields={"lastPrice": 1705.0, "preClose": 1700.0},
        )
    )

    assert event.event_type == "market.quote"
    assert event.payload["symbol"] == "600519.SH"
    assert event.payload["lastPrice"] == 1705.0


def test_normalize_announcement() -> None:
    event = normalize_announcement(
        AnnouncementRecord(
            symbol="600519.SH",
            time_ms=1703228400000,
            headline="2025 年度报告",
            url="http://example.com/a.pdf",
            source="cninfo",
        )
    )

    assert event.event_type == "market.announcement"
    assert event.payload["headline"] == "2025 年度报告"


def test_normalize_financial_fact() -> None:
    event = normalize_financial_fact(
        {
            "symbol": "600519.SH",
            "metric": "revenue",
            "period": "2025Q4",
            "value": "1200.00",
            "unit": "CNY",
            "source_id": "akshare",
        }
    )

    assert event.event_type == "financial.fact"
    assert event.payload["metric"] == "revenue"
    assert event.payload["value"] == "1200.00"


def test_event_ids_are_deterministic() -> None:
    first = normalize_quote(
        QuoteRecord(
            symbol="600519.SH",
            time_ms=1703228400000,
            fields={"lastPrice": 1705.0},
        )
    )
    second = normalize_quote(
        QuoteRecord(
            symbol="600519.SH",
            time_ms=1703228400000,
            fields={"lastPrice": 1705.0},
        )
    )

    assert first.event_id == second.event_id
