from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.pit import PitResolver
from stock_research.market.bar_service import MarketBarService

RISK_ENGINE_VERSION = "risk:1.0.0"

FINANCIAL_METRICS = (
    "total_assets",
    "total_liabilities",
    "total_equity",
    "current_assets",
    "current_liabilities",
    "operating_cash_flow",
)


@dataclass(frozen=True)
class RiskSnapshot:
    symbol: str
    as_of: datetime
    module_version: str
    data_versions: dict[str, object]
    financial_ratios: dict[str, Decimal | None]
    market_risk: dict[str, Decimal | None]
    risk_score: Decimal | None
    risk_level: str
    risk_action: str
    coverage: Decimal


class RiskEngine:
    """从 PIT 财务事实与历史 K 线确定性生成风险快照。"""

    module_version = RISK_ENGINE_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._resolver = PitResolver(session)
        self._bar_service = MarketBarService(session)

    async def calculate(
        self,
        symbol: str,
        as_of: datetime,
        period: str = "1d",
        limit: int = 252,
    ) -> RiskSnapshot:
        metrics, data_versions = await self._resolve_financial_metrics(symbol, as_of)
        financial_ratios = _financial_ratios(metrics)

        bars = await self._bar_service.bars(symbol, period, limit)
        market_risk = _market_risk(bars)
        data_versions["market"] = {
            "period": period,
            "bar_count": len(bars),
        }

        score, level, coverage = _risk_classification(financial_ratios, market_risk)
        return RiskSnapshot(
            symbol=symbol,
            as_of=as_of,
            module_version=self.module_version,
            data_versions=data_versions,
            financial_ratios=financial_ratios,
            market_risk=market_risk,
            risk_score=score,
            risk_level=level,
            risk_action=_risk_action(level),
            coverage=coverage,
        )

    async def _resolve_financial_metrics(
        self,
        symbol: str,
        as_of: datetime,
    ) -> tuple[dict[str, Decimal | None], dict[str, object]]:
        metrics: dict[str, Decimal | None] = {}
        data_versions: dict[str, object] = {}
        for metric in FINANCIAL_METRICS:
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
        return metrics, data_versions


def _financial_ratios(
    metrics: dict[str, Decimal | None],
) -> dict[str, Decimal | None]:
    total_assets = metrics["total_assets"]
    total_liabilities = metrics["total_liabilities"]
    total_equity = metrics["total_equity"]
    current_assets = metrics["current_assets"]
    current_liabilities = metrics["current_liabilities"]
    operating_cash_flow = metrics["operating_cash_flow"]

    return {
        "leverage_ratio": _ratio(total_liabilities, total_equity),
        "equity_ratio": _ratio(total_equity, total_assets),
        "current_ratio": _ratio(current_assets, current_liabilities),
        "cash_flow_to_current_liabilities": _ratio(
            operating_cash_flow,
            current_liabilities,
        ),
    }


def _market_risk(bars: Sequence[object]) -> dict[str, Decimal | None]:
    raw_closes = [_decimal_close(bar) for bar in bars]
    closes = [value for value in raw_closes if value is not None]
    if len(closes) < 2:
        return {"annualized_volatility": None, "max_drawdown": None}

    returns = [
        closes[index] / closes[index - 1] - Decimal("1")
        for index in range(1, len(closes))
    ]
    volatility = _standard_deviation(returns)
    if volatility is None:
        return {"annualized_volatility": None, "max_drawdown": None}

    annualized = volatility * Decimal("252").sqrt()
    max_drawdown = _max_drawdown(closes)
    return {
        "annualized_volatility": annualized,
        "max_drawdown": max_drawdown,
    }


def _risk_classification(
    financial_ratios: Mapping[str, Decimal | None],
    market_risk: Mapping[str, Decimal | None],
) -> tuple[Decimal | None, str, Decimal]:
    components = {
        "leverage_ratio": financial_ratios["leverage_ratio"],
        "current_ratio": financial_ratios["current_ratio"],
        "cash_flow_to_current_liabilities": financial_ratios[
            "cash_flow_to_current_liabilities"
        ],
        "annualized_volatility": market_risk["annualized_volatility"],
    }
    available = {key: value for key, value in components.items() if value is not None}
    if not available:
        return None, "UNKNOWN", Decimal("0")

    coverage = Decimal(len(available)) / Decimal(len(components))
    score = sum(
        (_component_score(key, value) for key, value in available.items()),
        Decimal("0"),
    ) / Decimal(len(available))

    if score >= Decimal("0.66"):
        level = "HIGH"
    elif score >= Decimal("0.33"):
        level = "MEDIUM"
    else:
        level = "LOW"
    return score, level, coverage


def _risk_action(risk_level: str) -> str:
    """把风险等级映射为风险动作：WATCH / RESTRICT / BLOCK。"""
    if risk_level == "HIGH":
        return "BLOCK"
    if risk_level == "MEDIUM":
        return "RESTRICT"
    return "WATCH"


def _component_score(key: str, value: Decimal) -> Decimal:
    if key == "leverage_ratio":
        return _clamp(value / Decimal("3"))
    if key == "current_ratio":
        return _clamp(Decimal("1") - value / Decimal("2"))
    if key == "cash_flow_to_current_liabilities":
        return _clamp(Decimal("1") - value)
    if key == "annualized_volatility":
        return _clamp(value / Decimal("0.6"))
    raise ValueError(f"unsupported risk component: {key}")


def _clamp(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        return Decimal("0")
    if value > Decimal("1"):
        return Decimal("1")
    return value


def _decimal_close(bar: object) -> Decimal | None:
    close = getattr(bar, "close", None)
    if close is None:
        return None
    return Decimal(str(close))


def _standard_deviation(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    mean = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum(
        ((value - mean) ** 2 for value in values),
        Decimal("0"),
    ) / Decimal(len(values))
    return variance.sqrt()


def _max_drawdown(closes: Sequence[Decimal]) -> Decimal:
    peak = closes[0]
    max_drawdown = Decimal("0")
    for close in closes[1:]:
        if close > peak:
            peak = close
        drawdown = (peak - close) / peak if peak else Decimal("0")
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    return max_drawdown


def _ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator
