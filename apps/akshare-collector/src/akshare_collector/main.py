import asyncio

from akshare_collector.app import Collector
from akshare_collector.config.settings import get_settings
from akshare_collector.observability.logging import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(Collector(settings).run())


if __name__ == "__main__":
    main()
