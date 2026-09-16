from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.store import FinancialFactStore
from stock_research.stores.models.fundamental import FinancialFact

PROFESSIONAL_FINANCIAL_VERSION = "professional_financial:1.0.0"

INPUT_METRICS = (
    "revenue",
    "cost_of_revenue",
    "operating_income",
    "net_income",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "current_assets",
    "current_liabilities",
    "inventory",
    "operating_cash_flow",
    "capital_expenditure",
    "interest_expense",
)


@dataclass(frozen=True)
class ProfessionalFinancialSnapshot:
    symbol: str
    as_of: datetime
    module_version: str
    metrics: dict[str, Decimal | None]
    ratios: dict[str, Decimal | None]
    growth: dict[str, Decimal | None]
    dupont: dict[str, Decimal | None]
    free_cash_flow: Decimal | None
    risk_points: tuple[str, ...]
    coverage: Decimal


class ProfessionalFinancialEngine:
    """专业财务分析 Engine，只使用 PIT financial_fact，不调用 LLM 计算。"""

    module_version = PROFESSIONAL_FINANCIAL_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._store = FinancialFactStore(session)

    async def calculate(
        self,
        symbol: str,
        as_of: datetime,
    ) -> ProfessionalFinancialSnapshot:
        facts = await self._store.list_for_symbol(
            symbol=symbol,
            as_of=as_of,
            metrics=list(INPUT_METRICS),
        )
        by_metric = _facts_by_metric(facts)
        current = {
            metric: _current_value(by_metric.get(metric, []))
            for metric in INPUT_METRICS
        }
        previous = {
            metric: _previous_value(by_metric.get(metric, []))
            for metric in INPUT_METRICS
        }

        ratios = _calculate_ratios(current)
        growth = {
            "revenue": _growth(current["revenue"], previous["revenue"]),
            "net_income": _growth(current["net_income"], previous["net_income"]),
            "operating_cash_flow": _growth(
                current["operating_cash_flow"],
                previous["operating_cash_flow"],
            ),
        }
        free_cash_flow = _sub(
            current["operating_cash_flow"],
            current["capital_expenditure"],
        )
        risk_points = _risk_points(current, ratios, free_cash_flow)
        present = [value for value in current.values() if value is not None]

        return ProfessionalFinancialSnapshot(
            symbol=symbol,
            as_of=as_of,
            module_version=self.module_version,
            metrics=current,
            ratios=ratios,
            growth=growth,
            dupont={
                "net_margin": ratios["net_margin"],
                "asset_turnover": _ratio(
                    current["revenue"],
                    current["total_assets"],
                ),
                "equity_multiplier": _ratio(
                    current["total_assets"],
                    current["total_equity"],
                ),
            },
            free_cash_flow=free_cash_flow,
            risk_points=risk_points,
            coverage=(
                Decimal(len(present)) / Decimal(len(INPUT_METRICS))
                if INPUT_METRICS
                else Decimal("0")
            ),
        )


def _facts_by_metric(
    facts: list[FinancialFact],
) -> dict[str, list[FinancialFact]]:
    grouped: dict[str, list[FinancialFact]] = {}
    for fact in facts:
        grouped.setdefault(fact.metric, []).append(fact)
    return grouped


def _current_value(facts: list[FinancialFact]) -> Decimal | None:
    if not facts:
        return None
    return facts[0].value


def _previous_value(facts: list[FinancialFact]) -> Decimal | None:
    if len(facts) < 2:
        return None
    current_period = facts[0].period
    for fact in facts[1:]:
        if fact.period != current_period:
            return fact.value
    return None


def _calculate_ratios(
    metrics: dict[str, Decimal | None],
) -> dict[str, Decimal | None]:
    return {
        "gross_margin": _ratio(
            _sub(metrics["revenue"], metrics["cost_of_revenue"]),
            metrics["revenue"],
        ),
        "net_margin": _ratio(metrics["net_income"], metrics["revenue"]),
        "roe": _ratio(metrics["net_income"], metrics["total_equity"]),
        "roa": _ratio(metrics["net_income"], metrics["total_assets"]),
        "debt_to_equity": _ratio(
            metrics["total_liabilities"],
            metrics["total_equity"],
        ),
        "current_ratio": _ratio(
            metrics["current_assets"],
            metrics["current_liabilities"],
        ),
        "quick_ratio": _ratio(
            _sub(metrics["current_assets"], metrics["inventory"]),
            metrics["current_liabilities"],
        ),
        "interest_coverage": _ratio(
            metrics["operating_income"],
            metrics["interest_expense"],
        ),
        "operating_cash_flow_to_net_income": _ratio(
            metrics["operating_cash_flow"],
            metrics["net_income"],
        ),
    }


def _risk_points(
    metrics: dict[str, Decimal | None],
    ratios: dict[str, Decimal | None],
    free_cash_flow: Decimal | None,
) -> tuple[str, ...]:
    points: list[str] = []
    if metrics["net_income"] is not None and metrics["net_income"] < 0:
        points.append("净利润为负")
    if metrics["operating_cash_flow"] is not None and metrics["operating_cash_flow"] < 0:
        points.append("经营现金流为负")
    if free_cash_flow is not None and free_cash_flow < 0:
        points.append("自由现金流为负")
    if ratios["current_ratio"] is not None and ratios["current_ratio"] < 1:
        points.append("流动比率低于1")
    if ratios["quick_ratio"] is not None and ratios["quick_ratio"] < 1:
        points.append("速动比率低于1")
    if ratios["debt_to_equity"] is not None and ratios["debt_to_equity"] > 2:
        points.append("负债权益比高于2")
    if (
        ratios["operating_cash_flow_to_net_income"] is not None
        and ratios["operating_cash_flow_to_net_income"] < Decimal("0.5")
    ):
        points.append("盈利现金含量不足")
    if (
        ratios["interest_coverage"] is not None
        and ratios["interest_coverage"] < Decimal("1.5")
    ):
        points.append("利息保障倍数偏低")
    return tuple(points)


def _growth(
    current: Decimal | None,
    previous: Decimal | None,
) -> Decimal | None:
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / previous


def _sub(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if left is None or right is None:
        return None
    return left - right


def _ratio(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> Decimal | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _decimal_str(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def professional_summary(
    snapshot: ProfessionalFinancialSnapshot,
) -> str:
    parts: list[str] = []
    net_income = snapshot.metrics["net_income"]
    revenue_growth = snapshot.growth["revenue"]
    net_income_growth = snapshot.growth["net_income"]
    roe = snapshot.ratios["roe"]
    if net_income is not None:
        parts.append(f"净利润 {net_income} 元")
    if revenue_growth is not None:
        parts.append(f"营收同比 {revenue_growth:.2%}")
    if net_income_growth is not None:
        parts.append(f"净利润同比 {net_income_growth:.2%}")
    if roe is not None:
        parts.append(f"ROE {roe:.2%}")
    if not parts:
        return f"{snapshot.symbol} 暂无足够专业财务数据。"
    return f"{snapshot.symbol} 专业财务概况：" + "，".join(parts) + "。"


def professional_payload(
    snapshot: ProfessionalFinancialSnapshot,
) -> dict[str, Any]:
    return {
        "metrics": {
            key: _decimal_str(value)
            for key, value in snapshot.metrics.items()
        },
        "ratios": {
            key: _decimal_str(value)
            for key, value in snapshot.ratios.items()
        },
        "growth": {
            key: _decimal_str(value)
            for key, value in snapshot.growth.items()
        },
        "dupont": {
            key: _decimal_str(value)
            for key, value in snapshot.dupont.items()
        },
        "free_cash_flow": _decimal_str(snapshot.free_cash_flow),
        "risk_points": list(snapshot.risk_points),
    }
