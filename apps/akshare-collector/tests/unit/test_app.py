import asyncio

from akshare_collector.app import Collector, _next_backoff
from akshare_collector.config.settings import CollectorSettings
from akshare_collector.sources.akshare import AkShareMarketSource
from akshare_collector.sources.financial import JsonLinesFinancialFactProvider
from akshare_collector.sources.tushare_financial import TushareFinancialFactProvider
from akshare_collector.sources.tushare_market import TushareMarketSource


def test_collector_defaults_to_akshare_and_jsonl() -> None:
    settings = CollectorSettings(_env_file=None)  # type: ignore[call-arg]
    collector = Collector(settings)
    try:
        assert isinstance(collector.market_source, AkShareMarketSource)
        assert isinstance(collector.financial_provider, JsonLinesFinancialFactProvider)
    finally:
        asyncio.run(collector.ingest_client.aclose())


def test_collector_uses_tushare_sources() -> None:
    settings = CollectorSettings(  # type: ignore[call-arg]
        _env_file=None,
        market_source="tushare",
        tushare_token="token",
        financial_source="tushare",
    )
    collector = Collector(settings)
    try:
        assert isinstance(collector.market_source, TushareMarketSource)
        assert isinstance(collector.financial_provider, TushareFinancialFactProvider)
    finally:
        asyncio.run(collector.ingest_client.aclose())


def test_next_backoff_doubles_until_maximum() -> None:
    backoff = 1.0
    seen = []
    for _ in range(8):
        backoff = _next_backoff(backoff, base=1.0, maximum=60.0)
        seen.append(backoff)

    assert seen == [2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0, 60.0]
