from __future__ import annotations

from datetime import datetime, timezone

from stock_research.agents.protocol import AgentContext, AgentResult
from stock_research.agents.react_skills import ResearchContextSkill
from stock_research.agents.report_pipeline import (
    StructuredReportAgent,
    StructuredReportResult,
    StructuredReportSection,
    StructuredReviewAgent,
)
from stock_research.agents.research_summary import ResearchSummaryResult
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


def _research() -> ResearchSummaryResult:
    return ResearchSummaryResult(
        symbol="600519.SH",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        module_version="research_summary:1.0.0",
        status="COMPLETED",
        module_summaries={
            "risk": {"status": "COMPLETED", "risk_level": "MEDIUM"},
        },
        coverage=1.0,
        summary_text="确定性汇总",
    )


def _report_context() -> AgentContext:
    return AgentContext(
        task_id="task-1",
        symbol="600519.SH",
        mode="standard",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        scopes=frozenset({"research.standard.execute"}),
        state={
            "results": {
                "research": AgentResult(
                    agent="research",
                    status="COMPLETED",
                    data={"result": _research()},
                )
            }
        },
    )


async def test_report_agent_adds_model_narrative() -> None:
    agent = StructuredReportAgent(
        model_gateway=ModelGateway(
            _FakeClient(
                ModelResponse(
                    content='{"final_answer":"模型报告叙述"}',
                    model="fake-model",
                )
            )
        ),
        skill_gateway=_gateway(),
    )

    result = await agent.run(_report_context())

    report = result.data["result"]
    assert result.warnings == ()
    assert report.summary == "确定性汇总"
    assert report.narrative == "模型报告叙述"
    assert report.react_trace is not None


async def test_report_agent_falls_back_to_deterministic_report() -> None:
    agent = StructuredReportAgent(
        model_gateway=ModelGateway(_FakeClient(RuntimeError("model down"))),
        skill_gateway=_gateway(),
    )

    result = await agent.run(_report_context())

    report = result.data["result"]
    assert result.warnings
    assert report.summary == "确定性汇总"
    assert report.narrative is None


async def test_review_agent_keeps_deterministic_decision_and_adds_note() -> None:
    report = StructuredReportResult(
        symbol="600519.SH",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        module_version="report:1.1.0",
        summary="测试汇总",
        sections=(StructuredReportSection("风险", {"risk_level": "HIGH"}),),
    )
    context = AgentContext(
        task_id="task-1",
        symbol="600519.SH",
        mode="standard",
        scopes=frozenset({"research.standard.execute"}),
        state={
            "results": {
                "report": AgentResult(
                    agent="report",
                    status="COMPLETED",
                    data={"result": report},
                )
            }
        },
    )
    agent = StructuredReviewAgent(
        model_gateway=ModelGateway(
            _FakeClient(
                ModelResponse(
                    content='{"final_answer":"建议关注高风险回撤"}',
                    model="fake-model",
                )
            )
        ),
        skill_gateway=_gateway(),
    )

    result = await agent.run(context)

    review = result.data["result"]
    assert result.warnings == ()
    assert review.decision == "NEEDS_REVISION"
    assert review.review_note == "建议关注高风险回撤"
    assert review.react_trace is not None
