from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelDescriptor:
    alias: str
    model_id: str
    capabilities: frozenset[str]
    priority: int


class ModelDiscoveryService:
    """模型别名解析，支持能力过滤和优先级。"""

    def __init__(self) -> None:
        self._models: dict[str, list[ModelDescriptor]] = {}

    def register(self, descriptor: ModelDescriptor) -> None:
        self._models.setdefault(descriptor.alias, []).append(descriptor)
        self._models[descriptor.alias].sort(key=lambda item: item.priority, reverse=True)

    def resolve(self, alias: str, capability: str | None = None) -> str | None:
        candidates = self._models.get(alias, [])
        if capability is not None:
            candidates = [
                candidate for candidate in candidates if capability in candidate.capabilities
            ]
        return candidates[0].model_id if candidates else None
