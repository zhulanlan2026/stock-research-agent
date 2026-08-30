from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict


class ResearchGraphState(TypedDict):
    task_id: str
    current_stage: str
    results: dict[str, Any]


class LinearResearchGraph:
    """线性图执行器，LangGraph 不可用时作为确定性 fallback。"""

    async def run(
        self,
        state: ResearchGraphState,
        stages: list[tuple[str, Callable[[dict[str, Any]], Any]]],
    ) -> ResearchGraphState:
        current: dict[str, Any] = dict(state)
        for stage_name, handler in stages:
            current["current_stage"] = stage_name
            current["results"][stage_name] = handler(current)
        return ResearchGraphState(
            task_id=str(current["task_id"]),
            current_stage=str(current["current_stage"]),
            results=current["results"],
        )
