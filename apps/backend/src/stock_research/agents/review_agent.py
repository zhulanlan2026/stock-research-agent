from __future__ import annotations

from dataclasses import dataclass

from stock_research.fundamental.report import ReportResult


@dataclass(frozen=True)
class ReviewAgentResult:
    agent: str
    decision: str
    reason: str


class ReviewAgent:
    """审核 Agent，当前做确定性报告审核。"""

    name = "review"

    async def review(self, report: ReportResult) -> ReviewAgentResult:
        if not report.sections:
            return ReviewAgentResult(self.name, "REJECTED", "报告缺少章节")

        risk_section = next(
            (section for section in report.sections if section.title == "风险"),
            None,
        )
        if risk_section is not None and risk_section.data.get("risk_level") == "HIGH":
            return ReviewAgentResult(self.name, "NEEDS_REVISION", "风险等级为 HIGH")

        return ReviewAgentResult(self.name, "APPROVED", "报告审核通过")
