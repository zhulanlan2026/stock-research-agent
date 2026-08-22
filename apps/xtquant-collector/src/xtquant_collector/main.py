import argparse
import asyncio

from xtquant_collector.app import Collector
from xtquant_collector.config.settings import CollectorSettings
from xtquant_collector.observability.logging import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="XTQuant collector")
    parser.parse_args()

    settings = CollectorSettings()
    configure_logging(settings.log_level)
    asyncio.run(Collector(settings).run())


if __name__ == "__main__":
    main()
