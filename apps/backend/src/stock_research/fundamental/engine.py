from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.pit import PitResolver

FUNDAMENTAL_ENGINE_VERSION = "fundamental:1.0.0"

INPUT_METRICS = (
    "revenue",
    "cost_of_revenue",
    "net_income",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "current_assets",
    "current_liabilities",
    "operating_cash_flow",
)


@dataclass(frozen=True)
class FundamentalSnapshot:
    symbol: str
    as_of: datetime
    module_version: str
    data_versions: dict[str, object]
    metrics: dict[str, Decimal | None]
    ratios: dict[str, Decimal | None]
    coverage: Decimal


class FundamentalEngine:
    """从 PIT financial_fact 确定性生成基本面快照。"""

    module_version = FUNDAMENTAL_ENGINE_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._resolver = PitResolver(session)

    async def calculate(self, symbol: str, as_of: datetime) -> FundamentalSnapshot:
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

        return FundamentalSnapshot(
            symbol=symbol,
            as_of=as_of,
            module_version=self.module_version,
            data_versions=data_versions,
            metrics=metrics,
            ratios=_calculate_ratios(metrics),
            coverage=coverage,
        )


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
        "operating_cash_flow_to_net_income": _ratio(
            metrics["operating_cash_flow"],
            metrics["net_income"],
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
