from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.risk import RiskEngine
from stock_research.fundamental.scenario import (
    ScenarioAssumption,
    ScenarioEngine,
    ScenarioPoint,
)

DECISION_ENGINE_VERSION = "decision:1.0.0"


@dataclass(frozen=True)
class DecisionSnapshot:
    symbol: str
    as_of: datetime
    module_version: str
    risk_level: str
    risk_score: Decimal | None
    base_implied_return: Decimal | None
    decision: str
    decision_score: Decimal | None
    rationale: str


class DecisionEngine:
    """将 Risk 与 Scenario 的确定性结果组合为决策快照。"""

    module_version = DECISION_ENGINE_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._risk_engine = RiskEngine(session)
        self._scenario_engine = ScenarioEngine(session)

    async def calculate(
        self,
        symbol: str,
        as_of: datetime,
        scenarios: list[ScenarioAssumption],
        price: Decimal | None = None,
    ) -> DecisionSnapshot:
        risk = await self._risk_engine.calculate(symbol, as_of)
        scenario = await self._scenario_engine.calculate(
            symbol,
            as_of,
            scenarios,
            price=price,
        )
        base_return = _base_implied_return(scenario.scenarios)
        decision, score, rationale = _decide(
            risk.risk_level,
            risk.risk_score,
            base_return,
        )
        return DecisionSnapshot(
            symbol=symbol,
            as_of=as_of,
            module_version=self.module_version,
            risk_level=risk.risk_level,
            risk_score=risk.risk_score,
            base_implied_return=base_return,
            decision=decision,
            decision_score=score,
            rationale=rationale,
        )


def _base_implied_return(scenarios: Sequence[ScenarioPoint]) -> Decimal | None:
    for scenario in scenarios:
        if scenario.name == "BASE":
            return scenario.implied_return
    return None


def _decide(
    risk_level: str,
    risk_score: Decimal | None,
    base_return: Decimal | None,
) -> tuple[str, Decimal | None, str]:
    if risk_level == "UNKNOWN" or risk_score is None or base_return is None:
        return "INSUFFICIENT_DATA", None, "风险或基准情景数据不足"

    if risk_level == "HIGH":
        score = base_return - Decimal("0.20")
        return "AVOID", score, "风险等级为 HIGH，优先规避"

    if risk_level == "LOW" and base_return > Decimal("0.05"):
        score = base_return
        return "ATTRACTIVE", score, "风险可控且基准情景隐含收益高于阈值"

    score = base_return - Decimal("0.05")
    return "HOLD", score, "风险与收益处于可接受但非显著区间"
