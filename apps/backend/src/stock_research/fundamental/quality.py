"""Deterministic earnings-quality engine.

C2-004 "CPA/Quality" is interpreted here as Cash flow / Profitability /
Accruals quality. The engine derives point-in-time quality ratios strictly from
``financial_fact`` rows resolved through the PIT resolver; no LLM output is
used to produce formal numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.pit import PitResolver

QUALITY_ENGINE_VERSION = "quality:1.0.0"

INPUT_METRICS = (
    "revenue",
    "net_income",
    "total_assets",
    "total_equity",
    "current_assets",
    "current_liabilities",
    "operating_cash_flow",
)


@dataclass(frozen=True)
class QualitySnapshot:
    symbol: str
    as_of: datetime
    module_version: str
    data_versions: dict[str, object]
    metrics: dict[str, Decimal | None]
    ratios: dict[str, Decimal | None]
    coverage: Decimal


class QualityEngine:
    """从 PIT financial_fact 确定性生成盈利质量快照。"""

    module_version = QUALITY_ENGINE_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._resolver = PitResolver(session)

    async def calculate(self, symbol: str, as_of: datetime) -> QualitySnapshot:
        metrics: dict[str, Decimal | None] = {}
        data_versions: dict[str, object] = {}

        for metric in INPUT_METRICS:
            resolved = await self._resolver.resolve(
                symbol=symbol,
                metric=metric,
                as_of=as_of,
            )
            if resolved is None:
                metrics[metric] = None
                continue
            metrics[metric] = resolved.value
            data_versions[metric] = {
                "period": resolved.period,
                "available_at": resolved.available_at.isoformat(),
                "revision_no": resolved.revision_no,
                "source_id": resolved.source_id,
            }

        present = [value for value in metrics.values() if value is not None]
        coverage = (
            Decimal(len(present)) / Decimal(len(INPUT_METRICS))
            if INPUT_METRICS
            else Decimal("0")
        )

        return QualitySnapshot(
            symbol=symbol,
            as_of=as_of,
            module_version=self.module_version,
            data_versions=data_versions,
            metrics=metrics,
            ratios=_calculate_quality_ratios(metrics),
            coverage=coverage,
        )


def _calculate_quality_ratios(
    metrics: dict[str, Decimal | None],
) -> dict[str, Decimal | None]:
    net_income = metrics["net_income"]
    operating_cash_flow = metrics["operating_cash_flow"]
    total_assets = metrics["total_assets"]
    revenue = metrics["revenue"]
    total_equity = metrics["total_equity"]
    current_assets = metrics["current_assets"]
    current_liabilities = metrics["current_liabilities"]

    return {
        "accrual_ratio": _ratio(
            _sub(net_income, operating_cash_flow),
            total_assets,
        ),
        "cash_conversion": _ratio(operating_cash_flow, net_income),
        "operating_cash_flow_margin": _ratio(operating_cash_flow, revenue),
        "asset_turnover": _ratio(revenue, total_assets),
        "equity_multiplier": _ratio(total_assets, total_equity),
        "working_capital_to_total_assets": _ratio(
            _sub(current_assets, current_liabilities),
            total_assets,
        ),
    }


def _sub(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if left is None or right is None:
        return None
    return left - right


def _ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator
