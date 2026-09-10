from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from stock_research.agents.protocol import Agent, AgentManifest


class DuplicateAgentError(ValueError):
    pass


class UnknownAgentError(KeyError):
    pass


class DependencyCycleError(ValueError):
    pass


@dataclass(frozen=True)
class AgentExecutionPlan:
    levels: tuple[tuple[str, ...], ...]
    flat: tuple[str, ...]


class AgentRegistry:
    """按名称注册 Agent，并提供依赖拓扑排序。"""

    def __init__(self, agents: Iterable[Agent] = ()) -> None:
        self._agents: dict[str, Agent] = {}
        for agent in agents:
            self.register(agent)

    def register(self, agent: Agent) -> None:
        name = agent.manifest.name
        if name in self._agents:
            raise DuplicateAgentError(f"agent already registered: {name}")
        self._agents[name] = agent

    def get(self, name: str) -> Agent:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise UnknownAgentError(f"unknown agent: {name}") from exc

    def manifests(self) -> tuple[AgentManifest, ...]:
        return tuple(agent.manifest for agent in self._agents.values())

    def resolve_order(self, requested: Sequence[str]) -> tuple[str, ...]:
        ordered: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                raise DependencyCycleError(f"agent dependency cycle at: {name}")
            agent = self.get(name)
            visiting.add(name)
            for dependency in agent.manifest.dependencies:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            ordered.append(name)

        for name in requested:
            visit(name)
        return tuple(ordered)

    def execution_plan(self, requested: Sequence[str]) -> AgentExecutionPlan:
        resolved = self.resolve_order(requested)
        remaining = set(resolved)
        levels: list[tuple[str, ...]] = []

        while remaining:
            level = tuple(
                name
                for name in resolved
                if name in remaining
                and all(
                    dependency not in remaining
                    for dependency in self.get(name).manifest.dependencies
                )
            )
            if not level:
                raise DependencyCycleError("agent dependency cycle detected")
            levels.append(level)
            remaining.difference_update(level)

        return AgentExecutionPlan(levels=tuple(levels), flat=resolved)
