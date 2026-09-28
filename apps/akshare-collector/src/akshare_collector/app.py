from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
import structlog

from akshare_collector.config.settings import CollectorSettings
from akshare_collector.events import (
    CollectorEvent,
    normalize_announcement,
    normalize_bar,
    normalize_financial_fact,
    normalize_quote,
)
from akshare_collector.sources.akshare import AkShareMarketSource
from akshare_collector.sources.financial import JsonLinesFinancialFactProvider
from akshare_collector.sources.records import BarRecord
from akshare_collector.sources.tushare import TushareCrossValidator
from akshare_collector.sources.tushare_financial import TushareFinancialFactProvider
from akshare_collector.sources.tushare_market import TushareMarketSource
from akshare_collector.transport import IngestClient, WALPump
from akshare_collector.wal import WalStore

logger = structlog.get_logger(__name__)


def _next_backoff(current: float, *, base: float, maximum: float) -> float:
    """指数退避，失败时翻倍，成功时由调用方重置为 base。"""
    return min(max(current * 2, base), maximum)


class Collector:
    def __init__(
        self,
        settings: CollectorSettings,
        *,
        market_source: AkShareMarketSource | TushareMarketSource | None = None,
        cross_validator: TushareCrossValidator | None = None,
    ) -> None:
        self.settings = settings
        self.wal = WalStore(settings.wal_path)
        self.ingest_client = IngestClient(settings.backend_url, settings.ingest_token)
        self.pump = WALPump(self.wal, self.ingest_client)
        if market_source is not None:
            self.market_source = market_source
        elif settings.market_source == "tushare":
            self.market_source = TushareMarketSource(
                settings.tushare_token,
                history_days=settings.bars_history_days,
                adjust=settings.tushare_adjust,
            )
        else:
            self.market_source = AkShareMarketSource(
                history_days=settings.bars_history_days
            )
        self.cross_validator = cross_validator or TushareCrossValidator(
            settings.tushare_token,
            settings.cross_validation_tolerance,
        )
        self.financial_provider: JsonLinesFinancialFactProvider | TushareFinancialFactProvider
        if settings.financial_source == "tushare":
            self.financial_provider = TushareFinancialFactProvider(
                settings.tushare_token,
                history_days=settings.history_days,
            )
        else:
            self.financial_provider = JsonLinesFinancialFactProvider(
                settings.financial_data_path
            )

    async def run(self) -> None:
        logger.info("collector starting", backend_url=self.settings.backend_url)
        self.wal.initialize()
        logger.info("collector WAL ready", wal_path=str(self.wal.path))

        symbols = self.settings.symbol_list
        if symbols:
            self._collect_bars(symbols)
            self._collect_quotes(symbols)
            if self.settings.collect_news_enabled:
                self._collect_announcements(symbols)
            if self.settings.collect_financial_enabled:
                self._collect_financial_facts(symbols)

        poll = self.settings.poll_interval_seconds
        backoff = poll
        last_quote_refresh = datetime.now(timezone.utc)
        last_bars_refresh = datetime.now(timezone.utc)
        try:
            while True:
                try:
                    shipped = await self.pump.drain_once()
                except httpx.HTTPError:
                    if backoff == poll:
                        logger.warning("collector ingest unavailable, backing off")
                    shipped = 0
                    backoff = _next_backoff(backoff, base=poll, maximum=60.0)
                else:
                    if backoff != poll:
                        logger.info("collector ingest recovered")
                    backoff = poll
                    if shipped:
                        logger.info("collector shipped events", count=shipped)

                elapsed = (datetime.now(timezone.utc) - last_quote_refresh).total_seconds()
                if symbols and elapsed >= self.settings.quote_refresh_seconds:
                    self._collect_quotes(symbols)
                    last_quote_refresh = datetime.now(timezone.utc)

                bars_elapsed = (
                    datetime.now(timezone.utc) - last_bars_refresh
                ).total_seconds()
                if symbols and bars_elapsed >= self.settings.bars_refresh_seconds:
                    self._collect_bars(symbols)
                    last_bars_refresh = datetime.now(timezone.utc)

                await asyncio.sleep(backoff)
        finally:
            await self.ingest_client.aclose()
            logger.info("collector stopped")

    def _collect_bars(self, symbols: list[str]) -> None:
        for period in self.settings.period_list:
            try:
                bars = self.market_source.fetch_bars(symbols, period)
            except Exception:
                logger.exception(
                    "market bars fetch failed",
                    source=self.market_source.name,
                    period=period,
                )
                continue
            self._append([normalize_bar(bar) for bar in bars])
            logger.info(
                "market bars fetched",
                source=self.market_source.name,
                period=period,
                count=len(bars),
            )
            if (
                period == "1d"
                and self.settings.cross_validation_active
                and isinstance(self.market_source, AkShareMarketSource)
            ):
                self._cross_validate(symbols, bars)

    def _cross_validate(self, symbols: list[str], bars: list[BarRecord]) -> None:
        for symbol in symbols:
            symbol_bars = [bar for bar in bars if bar.symbol == symbol]
            try:
                mismatches = self.cross_validator.validate(symbol, symbol_bars)
            except Exception:
                logger.exception("tushare cross validation failed", symbol=symbol)
                continue
            for message in mismatches:
                logger.warning("cross validation mismatch", message=message)

    def _collect_quotes(self, symbols: list[str]) -> None:
        try:
            quotes = self.market_source.fetch_quotes(symbols)
        except Exception:
            logger.exception("market quotes fetch failed", source=self.market_source.name)
            return
        self._append([normalize_quote(quote) for quote in quotes])
        logger.info(
            "market quotes fetched",
            source=self.market_source.name,
            count=len(quotes),
        )

    def _collect_announcements(self, symbols: list[str]) -> None:
        try:
            announcements = self.market_source.fetch_announcements(symbols)
        except Exception:
            logger.exception(
                "market announcements fetch failed",
                source=self.market_source.name,
            )
            return
        self._append([normalize_announcement(item) for item in announcements])
        logger.info(
            "market announcements fetched",
            source=self.market_source.name,
            count=len(announcements),
        )

    def _collect_financial_facts(self, symbols: list[str]) -> None:
        try:
            records = self.financial_provider.load(symbols)
        except Exception:
            logger.exception("financial facts load failed")
            return
        events: list[CollectorEvent] = []
        for record in records:
            try:
                events.append(normalize_financial_fact(record))
            except ValueError:
                logger.exception("financial fact normalization failed")
        self._append(events)
        logger.info("financial facts fetched", count=len(events))

    def _append(self, events: list[CollectorEvent]) -> None:
        for event in events:
            self.wal.append(event.event_id, event.event_type, event.payload)
