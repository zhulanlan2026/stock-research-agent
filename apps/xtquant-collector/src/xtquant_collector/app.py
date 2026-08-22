import asyncio

import structlog

from xtquant_collector.config.settings import CollectorSettings

logger = structlog.get_logger(__name__)


class Collector:
    def __init__(self, settings: CollectorSettings) -> None:
        self.settings = settings

    async def run(self) -> None:
        logger.info("collector starting", backend_url=self.settings.backend_url)
        try:
            while True:
                await asyncio.sleep(self.settings.poll_interval_seconds)
                logger.debug("collector heartbeat")
        finally:
            logger.info("collector stopped")
