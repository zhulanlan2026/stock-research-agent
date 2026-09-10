from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class AgentManifest:
    name: str
    version: str
    description: str = ""
    execution_type: str = "deterministic_engine"
    required_scopes: frozenset[str] = frozenset()
    allowed_skills: frozenset[str] = frozenset()
    external_model_allowed: bool = False
    side_effect: str = "NONE"
    dependencies: tuple[str, ...] = ()
    timeout_seconds: float = 30.0
    max_retries: int = 1


@dataclass(frozen=True)
class AgentContext:
    task_id: str
    symbol: str
    mode: str
    as_of: datetime | None = None
    purpose: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    scopes: frozenset[str] = frozenset()
    state: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentResult:
    agent: str
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    module_versions: dict[str, str] = field(default_factory=dict)
    latency_ms: int | None = None


class Agent(Protocol):
    @property
    def manifest(self) -> AgentManifest:
        ...

    async def run(self, context: AgentContext) -> AgentResult:
        ...
