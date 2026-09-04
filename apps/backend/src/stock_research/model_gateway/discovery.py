from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class RolloutDecider(Protocol):
    async def is_enabled(
        self,
        key: str,
        *,
        environment: str = "production",
        tenant_id: str | None = None,
        user_id: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        ...


@dataclass(frozen=True)
class ModelDescriptor:
    alias: str
    model_id: str
    capabilities: frozenset[str]
    priority: int
    rollout_key: str | None = None


class ModelDiscoveryService:
    """模型别名解析，支持能力过滤和优先级。"""

    def __init__(self) -> None:
        self._models: dict[str, list[ModelDescriptor]] = {}

    def register(self, descriptor: ModelDescriptor) -> None:
        self._models.setdefault(descriptor.alias, []).append(descriptor)
        self._models[descriptor.alias].sort(key=lambda item: item.priority, reverse=True)

    async def resolve(
        self,
        alias: str,
        capability: str | None = None,
        *,
        decider: RolloutDecider | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        now: datetime | None = None,
    ) -> str | None:
        candidates = self._models.get(alias, [])
        if capability is not None:
            candidates = [
                candidate for candidate in candidates if capability in candidate.capabilities
            ]
        for candidate in candidates:
            if candidate.rollout_key is not None:
                if decider is None:
                    continue
                if not await decider.is_enabled(
                    candidate.rollout_key,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    now=now,
                ):
                    continue
            return candidate.model_id
        return None
