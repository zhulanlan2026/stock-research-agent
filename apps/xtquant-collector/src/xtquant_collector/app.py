import asyncio

import httpx
import structlog

from xtquant_collector.config.settings import CollectorSettings
from xtquant_collector.transport.ingest import IngestClient, WALPump
from xtquant_collector.wal import WalStore
from xtquant_collector.xtquant import (
    MarketDataSource,
    QuoteEvent,
    XtQuantBarFetcher,
    XtQuantMarketDataSource,
)

logger = structlog.get_logger(__name__)


class Collector:
    def __init__(
        self,
        settings: CollectorSettings,
        *,
        data_source: MarketDataSource | None = None,
        bar_fetcher: XtQuantBarFetcher | None = None,
    ) -> None:
        self.settings = settings
        self.wal = WalStore(settings.wal_path)
        self.ingest_client = IngestClient(settings.backend_url, settings.ingest_token)
        self.pump = WALPump(self.wal, self.ingest_client)
        self.data_source = data_source if data_source is not None else XtQuantMarketDataSource()
        self.bar_fetcher = bar_fetcher if bar_fetcher is not None else XtQuantBarFetcher()
        self.event_queue: asyncio.Queue[QuoteEvent] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def run(self) -> None:
        logger.info("collector starting", backend_url=self.settings.backend_url)
        self.wal.initialize()
        logger.info("collector WAL ready", wal_path=str(self.wal.path))
        symbols = self.settings.symbol_list
        if symbols and self.settings.period_list:
            self._fetch_history_bars(symbols)
        self._loop = asyncio.get_running_loop()
        if symbols:
            self.data_source.start(symbols, self._enqueue_event)
            logger.info("xtquant collection started", symbols=symbols)
        try:
            while True:
                self._drain_event_queue()
                try:
                    shipped = await self.pump.drain_once()
                except httpx.HTTPError:
                    logger.exception("collector ingest failed")
                    shipped = 0
                if shipped:
                    logger.info("collector shipped events", count=shipped)
                await asyncio.sleep(self.settings.poll_interval_seconds)
        finally:
            if symbols:
                self.data_source.stop()
            await self.ingest_client.aclose()
            logger.info("collector stopped")

    def _fetch_history_bars(self, symbols: list[str]) -> None:
        for period in self.settings.period_list:
            try:
                bars = self.bar_fetcher.fetch(symbols, period, count=300)
            except Exception:
                logger.exception("xtquant history fetch failed", period=period)
                continue
            for bar in bars:
                self.wal.append(bar.event_id, bar.event_type, bar.payload)
            logger.info("xtquant history fetched", period=period, count=len(bars))

    def _enqueue_event(self, event: QuoteEvent) -> None:
        if self._loop is None:
            return
        try:
            self._loop.call_soon_threadsafe(self.event_queue.put_nowait, event)
        except RuntimeError:
            pass

    def _drain_event_queue(self) -> None:
        while True:
            try:
                event = self.event_queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            self.wal.append(event.event_id, event.event_type, event.payload)
