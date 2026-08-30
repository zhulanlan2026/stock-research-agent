from __future__ import annotations

from dataclasses import dataclass

from stock_research.fundamental.report import ReportResult, ReportService
from stock_research.fundamental.research import StandardResearchResult


@dataclass(frozen=True)
class ReportAgentResult:
    agent: str
    report: ReportResult


class ReportAgent:
    """报告 Agent，当前确定性渲染研究报告。"""

    name = "report"

    def __init__(self) -> None:
        self._service = ReportService()

    async def run(self, result: StandardResearchResult) -> ReportAgentResult:
        report = self._service.render(result)
        return ReportAgentResult(agent=self.name, report=report)
