from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.decision import DecisionEngine, DecisionSnapshot
from stock_research.fundamental.engine import FundamentalEngine, FundamentalSnapshot
from stock_research.fundamental.quality import QualityEngine, QualitySnapshot
from stock_research.fundamental.risk import RiskEngine, RiskSnapshot
from stock_research.fundamental.scenario import (
    ScenarioAssumption,
    ScenarioEngine,
    ScenarioSnapshot,
)
from stock_research.fundamental.valuation import ValuationEngine, ValuationSnapshot

SNAPSHOT_ENGINE_VERSION = "snapshot:1.0.0"


@dataclass(frozen=True)
class UnifiedSnapshot:
    symbol: str
    as_of: datetime
    module_version: str
    fundamental: FundamentalSnapshot
    quality: QualitySnapshot
    valuation: ValuationSnapshot
    risk: RiskSnapshot
    scenario: ScenarioSnapshot | None
    decision: DecisionSnapshot | None
    coverage: Decimal


class SnapshotEngine:
    """聚合各确定性引擎，形成一次完整的研究快照。"""

    module_version = SNAPSHOT_ENGINE_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._fundamental_engine = FundamentalEngine(session)
        self._quality_engine = QualityEngine(session)
        self._valuation_engine = ValuationEngine(session)
        self._risk_engine = RiskEngine(session)
        self._scenario_engine = ScenarioEngine(session)
        self._decision_engine = DecisionEngine(session)

    async def calculate(
        self,
        symbol: str,
        as_of: datetime,
        scenarios: list[ScenarioAssumption],
        price: Decimal | None = None,
    ) -> UnifiedSnapshot:
        fundamental = await self._fundamental_engine.calculate(symbol, as_of)
        quality = await self._quality_engine.calculate(symbol, as_of)
        valuation = await self._valuation_engine.calculate(
            symbol,
            as_of,
            price=price,
        )
        risk = await self._risk_engine.calculate(symbol, as_of)
        scenario = await self._scenario_engine.calculate(
            symbol,
            as_of,
            scenarios,
            price=price,
        )
        decision = await self._decision_engine.calculate(
            symbol,
            as_of,
            scenarios,
            price=price,
        )

        coverage = (
            fundamental.coverage
            + quality.coverage
            + valuation.coverage
            + risk.coverage
        ) / Decimal("4")

        return UnifiedSnapshot(
            symbol=symbol,
            as_of=as_of,
            module_version=self.module_version,
            fundamental=fundamental,
            quality=quality,
            valuation=valuation,
            risk=risk,
            scenario=scenario,
            decision=decision,
            coverage=coverage,
        )
