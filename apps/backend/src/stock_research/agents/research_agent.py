from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from stock_research.fundamental.research import StandardResearchResult, StandardResearchService
from stock_research.fundamental.scenario import ScenarioAssumption


@dataclass(frozen=True)
class ResearchAgentResult:
    agent: str
    result: StandardResearchResult


class ResearchAgent:
    """研究 Agent，当前确定性执行标准研究流程。"""

    name = "research"

    def __init__(self, service: StandardResearchService) -> None:
        self._service = service

    async def run(
        self,
        *,
        symbol: str,
        as_of: datetime,
        scenarios: list[ScenarioAssumption],
        peers: list[str] | None = None,
        price: Decimal | None = None,
    ) -> ResearchAgentResult:
        result = await self._service.run(
            symbol=symbol,
            as_of=as_of,
            scenarios=scenarios,
            peers=peers,
            price=price,
        )
        return ResearchAgentResult(agent=self.name, result=result)
