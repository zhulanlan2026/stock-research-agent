from __future__ import annotations

from datetime import datetime, timezone

from stock_research.agents.protocol import AgentContext
from stock_research.agents.react_skills import ResearchContextSkill
from stock_research.agents.research_summary import ResearchSummaryAgent
from stock_research.model_gateway.gateway import (
    ModelGateway,
    ModelRequest,
    ModelResponse,
)
from stock_research.skills.gateway import SkillGateway


class _FakeClient:
    def __init__(self, response: ModelResponse | Exception) -> None:
        self._response = response

    async def complete(self, request: ModelRequest) -> ModelResponse:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def _gateway() -> SkillGateway:
    gateway = SkillGateway()
    gateway.register_skill(
        ResearchContextSkill.manifest,
        ResearchContextSkill().execute,
    )
    return gateway


def _context() -> AgentContext:
    return AgentContext(
        task_id="task-1",
        symbol="600519.SH",
        mode="standard",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        purpose="生成研究结论",
        scopes=frozenset({"research.standard.execute"}),
        state={"results": {}},
    )


async def test_model_driven_research_replaces_summary_text() -> None:
    client = _FakeClient(
        ModelResponse(
            content='{"thought":"信息不足，直接给结论","final_answer":"模型结论"}',
            model="fake-model",
        )
    )
    agent = ResearchSummaryAgent(
        model_gateway=ModelGateway(client),
        skill_gateway=_gateway(),
    )

    result = await agent.run(_context())

    summary = result.data["result"]
    assert result.warnings == ()
    assert summary.summary_text == "模型结论"
    assert summary.react_trace is not None
    assert summary.react_trace["model_calls"] == 1


async def test_model_driven_research_falls_back_to_deterministic_summary() -> None:
    client = _FakeClient(RuntimeError("model unavailable"))
    agent = ResearchSummaryAgent(
        model_gateway=ModelGateway(client),
        skill_gateway=_gateway(),
    )

    result = await agent.run(_context())

    summary = result.data["result"]
    assert result.warnings
    assert "600519.SH" in summary.summary_text
    assert summary.react_trace is None
