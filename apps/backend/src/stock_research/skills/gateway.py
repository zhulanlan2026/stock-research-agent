from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from stock_research.skills.manifest import SkillManifest, SkillManifestRegistry


@dataclass(frozen=True)
class SkillCallContext:
    scopes: frozenset[str]
    agent: str
    task_id: str | None = None


class SkillDeniedError(RuntimeError):
    pass


class SkillGateway:
    """默认拒绝的 Skill 调用网关。"""

    def __init__(self) -> None:
        self.manifests = SkillManifestRegistry()
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register_skill(
        self,
        manifest: SkillManifest,
        handler: Callable[..., Any],
    ) -> None:
        self.manifests.register(manifest)
        self._handlers[manifest.name] = handler

    async def execute(
        self,
        skill_name: str,
        context: SkillCallContext,
        **kwargs: Any,
    ) -> Any:
        manifest = self.manifests.get(skill_name)
        if manifest is None:
            raise SkillDeniedError("skill not registered")
        if not context.scopes.intersection(manifest.required_scopes):
            raise SkillDeniedError("scope denied")
        handler = self._handlers.get(skill_name)
        if handler is None:
            raise SkillDeniedError("handler not registered")
        result = handler(**kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result
