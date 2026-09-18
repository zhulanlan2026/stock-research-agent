from __future__ import annotations

from datetime import datetime, timezone

from stock_research.agents.protocol import AgentContext, AgentResult
from stock_research.agents.report_pipeline import (
    StructuredReportAgent,
    StructuredReportResult,
    StructuredReportSection,
    StructuredReviewAgent,
)
from stock_research.agents.research_summary import ResearchSummaryResult


def _research_result(risk_level: str = "MEDIUM") -> ResearchSummaryResult:
    return ResearchSummaryResult(
        symbol="600519.SH",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        module_version="research_summary:1.0.0",
        status="COMPLETED",
        module_summaries={
            "fundamental": {"status": "COMPLETED", "roe": "0.15"},
            "technical": {"status": "COMPLETED", "rsi": 55.5},
            "market": {"status": "COMPLETED", "change_pct": 5.0},
            "supply_chain": {
                "status": "COMPLETED",
                "node_count": 2,
                "edge_count": 1,
            },
            "news": {"status": "COMPLETED", "item_count": 0},
            "risk": {"status": "COMPLETED", "risk_level": risk_level},
        },
        module_versions={
            "fundamental": "fundamental:1.0.0",
            "technical": "technical:1.1.0",
            "market": "market:1.0.0",
            "supply_chain": "supply_chain:1.0.0",
            "news": "news:1.1.0",
            "risk": "risk:1.0.0",
        },
        coverage=1.0,
        summary_text="测试汇总",
    )


async def test_report_agent_renders_research_summary() -> None:
    context = AgentContext(
        task_id="task-1",
        symbol="600519.SH",
        mode="standard",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        state={
            "results": {
                "research": AgentResult(
                    agent="research",
                    status="COMPLETED",
                    data={"result": _research_result()},
                )
            }
        },
    )

    result = await StructuredReportAgent().run(context)

    report = result.data["result"]
    assert report.summary == "测试汇总"
    assert [section.title for section in report.sections] == [
        "概览",
        "财务",
        "技术",
        "周期分析",
        "行情",
        "供应链",
        "新闻",
        "风险",
        "版本信息",
        "免责声明",
    ]
    financial = next(section for section in report.sections if section.title == "财务")
    assert "conclusion" in financial.data
    assert financial.data["conclusion"]


async def test_review_agent_requires_revision_for_high_risk() -> None:
    report = StructuredReportResult(
        symbol="600519.SH",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        module_version="report:1.0.0",
        summary="测试汇总",
        sections=(
            StructuredReportSection("风险", {"risk_level": "HIGH"}),
        ),
    )
    context = AgentContext(
        task_id="task-1",
        symbol="600519.SH",
        mode="standard",
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

    result = await StructuredReviewAgent().run(context)

    review = result.data["result"]
    assert review.decision == "NEEDS_REVISION"
