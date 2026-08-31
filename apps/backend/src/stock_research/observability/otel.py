from __future__ import annotations

from importlib.util import find_spec


class OtelConfigurator:
    """OTel 配置入口，依赖缺失时安全降级。"""

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name

    def configure(self) -> bool:
        if find_spec("opentelemetry") is None:
            return False
        return True
