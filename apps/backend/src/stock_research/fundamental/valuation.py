"""Deterministic valuation engine.

C2-006 "Valuation" is interpreted here as market-multiple valuation from
point-in-time financial facts and the latest market price. ``shares_outstanding``
is read as a financial fact metric, so no schema change is required.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.pit import PitResolver
from stock_research.market.analysis import MarketAnalysisService

VALUATION_ENGINE_VERSION = "valuation:1.0.0"

INPUT_METRICS = (
    "revenue",
    "net_income",
    "total_equity",
    "shares_outstanding",
)


@dataclass(frozen=True)
class ValuationSnapshot:
    symbol: str
    as_of: datetime
    module_version: str
    data_versions: dict[str, object]
    price: Decimal | None
    shares_outstanding: Decimal | None
    per_share: dict[str, Decimal | None]
    multiples: dict[str, Decimal | None]
    market_cap: Decimal | None
    coverage: Decimal


class ValuationEngine:
    """从 PIT 财务事实与最新行情价格确定性生成估值快照。"""

    module_version = VALUATION_ENGINE_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._resolver = PitResolver(session)
        self._market = MarketAnalysisService(session)

    async def calculate(
        self,
        symbol: str,
        as_of: datetime,
        price: Decimal | None = None,
    ) -> ValuationSnapshot:
        if price is None:
            summary = await self._market.summarize(symbol)
            price = _decimal_from_float(summary.last_price)

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
        per_share, multiples, market_cap = _valuation_values(price, metrics)
        data_versions["price"] = {"source": "market_snapshot_latest"}

        return ValuationSnapshot(
            symbol=symbol,
            as_of=as_of,
            module_version=self.module_version,
            data_versions=data_versions,
            price=price,
            shares_outstanding=metrics["shares_outstanding"],
            per_share=per_share,
            multiples=multiples,
            market_cap=market_cap,
            coverage=coverage,
        )


def _valuation_values(
    price: Decimal | None,
    metrics: dict[str, Decimal | None],
) -> tuple[
    dict[str, Decimal | None],
    dict[str, Decimal | None],
    Decimal | None,
]:
    shares = metrics["shares_outstanding"]
    revenue = metrics["revenue"]
    net_income = metrics["net_income"]
    total_equity = metrics["total_equity"]

    eps = _ratio(net_income, shares)
    bvps = _ratio(total_equity, shares)
    sps = _ratio(revenue, shares)

    per_share = {"eps": eps, "bvps": bvps, "sps": sps}
    multiples = {
        "pe": _ratio(price, eps),
        "pb": _ratio(price, bvps),
        "ps": _ratio(price, sps),
    }
    market_cap = _multiply(price, shares)
    return per_share, multiples, market_cap


def _ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _multiply(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if left is None or right is None:
        return None
    return left * right


def _decimal_from_float(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
