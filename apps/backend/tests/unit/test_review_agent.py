from datetime import datetime, timezone

from stock_research.agents.review_agent import ReviewAgent
from stock_research.fundamental.report import ReportResult, ReportSection


async def test_review_agent_approves_report() -> None:
    report = ReportResult(
        symbol="600519.SH",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        module_version="report:1.0.0",
        sections=[ReportSection("风险", {"risk_level": "LOW"})],
    )

    result = await ReviewAgent().review(report)

    assert result.decision == "APPROVED"


async def test_review_agent_rejects_empty_report() -> None:
    report = ReportResult(
        symbol="600519.SH",
        as_of=datetime(2026, 4, 1, tzinfo=timezone.utc),
        module_version="report:1.0.0",
        sections=[],
    )

    result = await ReviewAgent().review(report)

    assert result.decision == "REJECTED"
