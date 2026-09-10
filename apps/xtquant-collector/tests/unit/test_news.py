from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pytest

from xtquant_collector.xtquant import (
    XtQuantAnnouncementProvider,
    XtQuantNewsFetcher,
    normalize_news_item,
)
from xtquant_collector.xtquant.news import _grouped_announcement_records


def test_normalize_announcement_is_deterministic() -> None:
    raw = {
        "time": "20231222",
        "title": "重大合同公告",
        "url": "https://example.com/a",
        "source": "上交所",
    }

    first = normalize_news_item("600519.SH", "announcement", raw)
    second = normalize_news_item("600519.SH", "announcement", raw)

    assert first == second
    assert first.event_type == "market.announcement"
    assert first.payload["symbol"] == "600519.SH"
    assert first.payload["headline"] == "重大合同公告"
    assert first.payload["time"] == 1703203200000


def test_normalize_news_uses_field_aliases() -> None:
    event = normalize_news_item(
        "000001.SZ",
        "news",
        {
            "published_at": 1703228400000,
            "headline": "行业政策变化",
            "link": "https://example.com/n",
            "media": "财联社",
        },
    )

    assert event.event_type == "market.news"
    assert event.payload["headline"] == "行业政策变化"
    assert event.payload["url"] == "https://example.com/n"
    assert event.payload["source"] == "财联社"


def test_news_fetcher_uses_injected_raw_provider() -> None:
    def provider(symbols: Sequence[str], kind: str) -> dict[str, list[object]]:
        assert symbols == ["600519.SH"]
        assert kind == "announcement"
        return {
            "600519.SH": [
                {
                    "time": "20231222",
                    "title": "公告",
                }
            ]
        }

    events = XtQuantNewsFetcher(provider).fetch(["600519.SH"], "announcement")

    assert len(events) == 1
    assert events[0].event_type == "market.announcement"
    assert events[0].payload["headline"] == "公告"


def test_news_fetcher_requires_configured_provider() -> None:
    with pytest.raises(RuntimeError, match="provider is not configured"):
        XtQuantNewsFetcher().fetch(["600519.SH"], "announcement")


def test_announcement_provider_requires_xtquant() -> None:
    provider = XtQuantAnnouncementProvider()

    with pytest.raises(RuntimeError, match="xtquant is not installed"):
        provider(["600519.SH"], "announcement")


def test_announcement_provider_rejects_news_kind() -> None:
    with pytest.raises(RuntimeError, match="only announcement is supported"):
        XtQuantAnnouncementProvider()(["600519.SH"], "news")


def test_grouped_announcement_records_from_dataframe_keeps_index_time() -> None:
    frame = pd.DataFrame(
        {"title": ["重大合同公告"], "url": ["https://example.com/a"]},
        index=pd.Index(["20231222"], name="time"),
    )

    grouped = _grouped_announcement_records(
        {"600519.SH": frame},
        ["600519.SH"],
    )
    events = [
        normalize_news_item("600519.SH", "announcement", raw)
        for raw in grouped["600519.SH"]
    ]

    assert len(events) == 1
    assert events[0].payload["time"] == 1703203200000
    assert events[0].payload["headline"] == "重大合同公告"


def test_grouped_announcement_records_from_column_dict() -> None:
    grouped = _grouped_announcement_records(
        {
            "600519.SH": {
                "time": ["20231222", "20231223"],
                "title": ["公告一", "公告二"],
                "url": ["https://example.com/1", "https://example.com/2"],
            }
        },
        ["600519.SH"],
    )
    events = [
        normalize_news_item("600519.SH", "announcement", raw)
        for raw in grouped["600519.SH"]
    ]

    assert [event.payload["headline"] for event in events] == ["公告一", "公告二"]
