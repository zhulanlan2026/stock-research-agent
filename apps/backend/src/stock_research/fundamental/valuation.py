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

VALUATION_ENGINE_VERSION = "valuation:1.1.0"

INPUT_METRICS = (
    "revenue",
    "net_income",
    "total_equity",
    "shares_outstanding",
    "operating_cash_flow",
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
    peg: Decimal | None
    dcf: dict[str, Decimal | None]
    safety_margin: Decimal | None
    valuation_label: str
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
        *,
        earnings_growth: Decimal | None = None,
        discount_rate: Decimal = Decimal("0.10"),
        growth_rate: Decimal = Decimal("0.03"),
    ) -> ValuationSnapshot:
        if price is None:
            summary = await self._market.summarize(symbol, as_of=as_of)
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
        peg = _peg(multiples.get("pe"), earnings_growth)
        fcf_per_share = _ratio(
            metrics.get("operating_cash_flow"),
            metrics.get("shares_outstanding"),
        )
        dcf = _dcf(
            fcf_per_share,
            discount_rate=discount_rate,
            growth_rate=growth_rate,
        )
        intrinsic_value = dcf.get("intrinsic_value_per_share")
        safety_margin = _safety_margin(intrinsic_value, price)
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
            peg=peg,
            dcf=dcf,
            safety_margin=safety_margin,
            valuation_label=_valuation_label(safety_margin),
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


def _peg(pe: Decimal | None, earnings_growth: Decimal | None) -> Decimal | None:
    if pe is None or earnings_growth is None or earnings_growth <= 0:
        return None
    return pe / (earnings_growth * Decimal("100"))


def _dcf(
    fcf_per_share: Decimal | None,
    *,
    discount_rate: Decimal,
    growth_rate: Decimal,
) -> dict[str, Decimal | None]:
    if (
        fcf_per_share is None
        or fcf_per_share <= 0
        or discount_rate <= growth_rate
    ):
        return {
            "fcf_per_share": fcf_per_share,
            "discount_rate": discount_rate,
            "growth_rate": growth_rate,
            "intrinsic_value_per_share": None,
        }
    intrinsic_value = (
        fcf_per_share
        * (Decimal("1") + growth_rate)
        / (discount_rate - growth_rate)
    )
    return {
        "fcf_per_share": fcf_per_share,
        "discount_rate": discount_rate,
        "growth_rate": growth_rate,
        "intrinsic_value_per_share": intrinsic_value,
    }


def _safety_margin(
    intrinsic_value: Decimal | None,
    price: Decimal | None,
) -> Decimal | None:
    if intrinsic_value is None or price is None or intrinsic_value == 0:
        return None
    return (intrinsic_value - price) / intrinsic_value


def _valuation_label(safety_margin: Decimal | None) -> str:
    if safety_margin is None:
        return "数据不足"
    if safety_margin >= Decimal("0.15"):
        return "低估"
    if safety_margin <= Decimal("-0.15"):
        return "高估"
    return "合理"


def _decimal_from_float(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
