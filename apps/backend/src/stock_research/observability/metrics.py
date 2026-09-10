from __future__ import annotations

from functools import lru_cache

from stock_research.observability.prometheus import PrometheusRegistry


@lru_cache(maxsize=1)
def get_prometheus_registry() -> PrometheusRegistry:
    return PrometheusRegistry()
