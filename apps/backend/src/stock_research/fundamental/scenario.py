from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.valuation import ValuationEngine

SCENARIO_ENGINE_VERSION = "scenario:1.0.0"


@dataclass(frozen=True)
class ScenarioAssumption:
    name: str
    pe: Decimal


@dataclass(frozen=True)
class ScenarioPoint:
    name: str
    pe: Decimal
    target_price: Decimal | None
    implied_return: Decimal | None


@dataclass(frozen=True)
class ScenarioSnapshot:
    symbol: str
    as_of: datetime
    module_version: str
    current_price: Decimal | None
    eps: Decimal | None
    scenarios: list[ScenarioPoint]


class ScenarioEngine:
    """基于估值引擎和显式场景假设生成确定性目标价。"""

    module_version = SCENARIO_ENGINE_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._valuation_engine = ValuationEngine(session)

    async def calculate(
        self,
        symbol: str,
        as_of: datetime,
        scenarios: list[ScenarioAssumption],
        price: Decimal | None = None,
    ) -> ScenarioSnapshot:
        valuation = await self._valuation_engine.calculate(
            symbol,
            as_of,
            price=price,
        )
        eps = valuation.per_share["eps"]
        return ScenarioSnapshot(
            symbol=symbol,
            as_of=as_of,
            module_version=self.module_version,
            current_price=valuation.price,
            eps=eps,
            scenarios=[
                _scenario_point(
                    name=scenario.name,
                    pe=scenario.pe,
                    eps=eps,
                    current_price=valuation.price,
                )
                for scenario in scenarios
            ],
        )


def _scenario_point(
    *,
    name: str,
    pe: Decimal,
    eps: Decimal | None,
    current_price: Decimal | None,
) -> ScenarioPoint:
    target_price = _multiply(eps, pe)
    implied_return = (
        _ratio(target_price - current_price, current_price)
        if target_price is not None and current_price is not None and current_price != 0
        else None
    )
    return ScenarioPoint(
        name=name,
        pe=pe,
        target_price=target_price,
        implied_return=implied_return,
    )


def _multiply(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if left is None or right is None:
        return None
    return left * right


def _ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator
