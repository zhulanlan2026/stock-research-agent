from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from stock_research.agents.orchestrator import AgentOrchestrator
from stock_research.agents.protocol import AgentContext, AgentManifest, AgentResult
from stock_research.agents.registry import (
    AgentRegistry,
    DependencyCycleError,
    DuplicateAgentError,
    UnknownAgentError,
)


class _FakeAgent:
    def __init__(self, manifest: AgentManifest) -> None:
        self._manifest = manifest

    @property
    def manifest(self) -> AgentManifest:
        return self._manifest

    async def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(agent=self._manifest.name, status="COMPLETED")


def test_registry_resolves_dependencies() -> None:
    registry = AgentRegistry(
        [
            _FakeAgent(AgentManifest("fundamental", "1.0.0")),
            _FakeAgent(
                AgentManifest(
                    "risk",
                    "1.0.0",
                    dependencies=("fundamental", "technical"),
                )
            ),
            _FakeAgent(AgentManifest("technical", "1.0.0")),
            _FakeAgent(AgentManifest("report", "1.0.0", dependencies=("risk",))),
        ]
    )

    assert registry.resolve_order(["report"]) == (
        "fundamental",
        "technical",
        "risk",
        "report",
    )


def test_registry_rejects_duplicate_agent() -> None:
    registry = AgentRegistry([_FakeAgent(AgentManifest("technical", "1.0.0"))])

    with pytest.raises(DuplicateAgentError):
        registry.register(_FakeAgent(AgentManifest("technical", "2.0.0")))


def test_registry_rejects_unknown_dependency() -> None:
    registry = AgentRegistry(
        [_FakeAgent(AgentManifest("risk", "1.0.0", dependencies=("missing",)))]
    )

    with pytest.raises(UnknownAgentError):
        registry.resolve_order(["risk"])


def test_registry_rejects_dependency_cycle() -> None:
    registry = AgentRegistry(
        [
            _FakeAgent(AgentManifest("a", "1.0.0", dependencies=("b",))),
            _FakeAgent(AgentManifest("b", "1.0.0", dependencies=("a",))),
        ]
    )

    with pytest.raises(DependencyCycleError):
        registry.resolve_order(["a"])


def test_registry_builds_execution_levels() -> None:
    registry = AgentRegistry(
        [
            _FakeAgent(AgentManifest("fundamental", "1.0.0")),
            _FakeAgent(AgentManifest("technical", "1.0.0")),
            _FakeAgent(
                AgentManifest(
                    "risk",
                    "1.0.0",
                    dependencies=("fundamental", "technical"),
                )
            ),
            _FakeAgent(AgentManifest("report", "1.0.0", dependencies=("risk",))),
        ]
    )

    plan = registry.execution_plan(["report"])

    assert plan.levels == (
        ("fundamental", "technical"),
        ("risk",),
        ("report",),
    )
    assert plan.flat == ("fundamental", "technical", "risk", "report")


async def test_orchestrator_runs_independent_agents_in_parallel() -> None:
    active = 0
    max_active = 0
    lock = asyncio.Lock()

    class _SlowAgent(_FakeAgent):
        async def run(self, context: AgentContext) -> AgentResult:
            nonlocal active, max_active
            async with lock:
                active += 1
                max_active = max(max_active, active)
            await asyncio.sleep(0.05)
            async with lock:
                active -= 1
            return AgentResult(agent=self._manifest.name, status="COMPLETED")

    registry = AgentRegistry(
        [
            _SlowAgent(AgentManifest("fundamental", "1.0.0")),
            _SlowAgent(AgentManifest("technical", "1.0.0")),
        ]
    )
    orchestrator = AgentOrchestrator(registry, prefer_langgraph=False)

    result = await orchestrator.run(
        AgentContext(
            task_id="task-1",
            symbol="600519.SH",
            mode="standard",
        ),
        ["fundamental", "technical"],
    )

    assert max_active == 2
    assert set(result.results) == {"fundamental", "technical"}
    assert all(item.status == "COMPLETED" for item in result.results.values())


async def test_orchestrator_prefers_langgraph_when_available() -> None:
    registry = AgentRegistry(
        [
            _FakeAgent(AgentManifest("fundamental", "1.0.0")),
            _FakeAgent(AgentManifest("technical", "1.0.0")),
        ]
    )
    orchestrator = AgentOrchestrator(registry, prefer_langgraph=True)

    result = await orchestrator.run(
        AgentContext(
            task_id="task-1",
            symbol="600519.SH",
            mode="standard",
        ),
        ["fundamental", "technical"],
    )

    assert orchestrator.executor.__class__.__name__ == "LangGraphAgentExecutor"
    assert set(result.results) == {"fundamental", "technical"}


def test_agent_context_is_frozen() -> None:
    context = AgentContext(
        task_id="task-1",
        symbol="600519.SH",
        mode="standard",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )

    assert context.symbol == "600519.SH"
    assert context.state == {}
