from __future__ import annotations

import asyncio
import importlib
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Annotated, Any, Protocol, TypedDict

from stock_research.agents.protocol import AgentContext, AgentResult
from stock_research.agents.registry import AgentExecutionPlan, AgentRegistry


@dataclass(frozen=True)
class OrchestrationResult:
    results: dict[str, AgentResult]
    state: dict[str, Any]
    warnings: tuple[str, ...]


class AgentExecutionError(RuntimeError):
    pass


def _merge_results(
    left: dict[str, AgentResult],
    right: dict[str, AgentResult],
) -> dict[str, AgentResult]:
    merged = dict(left)
    for name, result in right.items():
        if name in merged and merged[name] != result:
            raise AgentExecutionError(f"conflicting agent result for: {name}")
        merged[name] = result
    return merged


def _merge_warnings(
    left: tuple[str, ...],
    right: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*left, *right)))


class _ResearchState(TypedDict, total=False):
    context: AgentContext
    results: Annotated[dict[str, AgentResult], _merge_results]
    warnings: Annotated[tuple[str, ...], _merge_warnings]


class AgentExecutor(Protocol):
    async def execute(
        self,
        registry: AgentRegistry,
        context: AgentContext,
        plan: AgentExecutionPlan,
    ) -> OrchestrationResult:
        ...


class ParallelAgentExecutor:
    """无 LangGraph 时的确定性并行执行器。"""

    async def execute(
        self,
        registry: AgentRegistry,
        context: AgentContext,
        plan: AgentExecutionPlan,
    ) -> OrchestrationResult:
        state = dict(context.state)
        results: dict[str, AgentResult] = {}
        warnings: list[str] = []

        for level in plan.levels:
            batch = await asyncio.gather(
                *(
                    self._run_agent(name, registry, context, state)
                    for name in level
                )
            )
            failed: list[str] = []
            for name, result in batch:
                results[name] = result
                state[name] = result.data
                state["results"] = dict(results)
                if result.status == "FAILED":
                    failed.append(name)
                warnings.extend(result.warnings)
            if failed:
                raise AgentExecutionError(
                    "agent execution failed: " + ", ".join(failed)
                )

        return OrchestrationResult(
            results=results,
            state=state,
            warnings=tuple(dict.fromkeys(warnings)),
        )

    async def _run_agent(
        self,
        name: str,
        registry: AgentRegistry,
        context: AgentContext,
        state: dict[str, Any],
    ) -> tuple[str, AgentResult]:
        agent = registry.get(name)
        agent_context = replace(context, state=state)
        started = time.perf_counter()
        try:
            result = await agent.run(agent_context)
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return (
                name,
                AgentResult(
                    agent=name,
                    status="FAILED",
                    data={"error": str(exc)},
                    warnings=(f"agent failed: {type(exc).__name__}",),
                    latency_ms=elapsed_ms,
                ),
            )

        if result.latency_ms is None:
            result = replace(
                result,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        return name, result


class LangGraphAgentExecutor:
    """LangGraph DAG 执行器；未安装 LangGraph 时由上层回退。"""

    async def execute(
        self,
        registry: AgentRegistry,
        context: AgentContext,
        plan: AgentExecutionPlan,
    ) -> OrchestrationResult:
        start, end, state_graph = _load_langgraph()
        graph_builder = state_graph(_ResearchState)

        for name in plan.flat:
            graph_builder.add_node(name, self._make_node(name, registry))

        first_level = plan.levels[0] if plan.levels else ()
        for name in first_level:
            graph_builder.add_edge(start, name)

        for index in range(len(plan.levels) - 1):
            previous = plan.levels[index]
            current = plan.levels[index + 1]
            for upstream in previous:
                for downstream in current:
                    graph_builder.add_edge(upstream, downstream)

        last_level = plan.levels[-1] if plan.levels else ()
        for name in last_level:
            graph_builder.add_edge(name, end)

        graph = graph_builder.compile()
        final_state = await graph.ainvoke(
            {
                "context": context,
                "results": {},
                "warnings": (),
            }
        )
        return _to_orchestration_result(final_state)

    def _make_node(
        self,
        name: str,
        registry: AgentRegistry,
    ) -> Any:
        async def node(state: dict[str, Any]) -> dict[str, Any]:
            agent = registry.get(name)
            context = replace(state["context"], state=state)
            started = time.perf_counter()
            result = await agent.run(context)
            if result.latency_ms is None:
                result = replace(
                    result,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
            return {
                "results": {name: result},
                "warnings": result.warnings,
            }

        return node


def _load_langgraph() -> tuple[Any, Any, Any]:
    try:
        graph_module = importlib.import_module("langgraph.graph")
        return graph_module.START, graph_module.END, graph_module.StateGraph
    except ImportError as exc:
        raise RuntimeError("langgraph is not installed") from exc


def _to_orchestration_result(state: dict[str, Any]) -> OrchestrationResult:
    results = state.get("results", {})
    warnings = state.get("warnings", ())
    data_state = {name: result.data for name, result in results.items()}
    return OrchestrationResult(
        results=results,
        state=data_state,
        warnings=tuple(warnings),
    )


class AgentOrchestrator:
    def __init__(
        self,
        registry: AgentRegistry,
        *,
        executor: AgentExecutor | None = None,
        prefer_langgraph: bool = True,
    ) -> None:
        self.registry = registry
        self.executor = executor or self._default_executor(prefer_langgraph)

    async def run(
        self,
        context: AgentContext,
        requested: Sequence[str],
    ) -> OrchestrationResult:
        plan = self.registry.execution_plan(requested)
        return await self.executor.execute(self.registry, context, plan)

    @staticmethod
    def _default_executor(prefer_langgraph: bool) -> AgentExecutor:
        if prefer_langgraph:
            try:
                _load_langgraph()
            except RuntimeError:
                return ParallelAgentExecutor()
            return LangGraphAgentExecutor()
        return ParallelAgentExecutor()
