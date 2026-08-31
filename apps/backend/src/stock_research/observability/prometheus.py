from __future__ import annotations

from collections import defaultdict


class PrometheusRegistry:
    """轻量 Prometheus 文本指标注册表。"""

    def __init__(self) -> None:
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = defaultdict(float)

    def inc_counter(self, name: str, value: float = 1.0) -> None:
        self._counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def render(self) -> str:
        lines: list[str] = []
        for name, value in sorted(self._counters.items()):
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, value in sorted(self._gauges.items()):
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        return "\n".join(lines) + ("\n" if lines else "")
