from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.pit import PitResolver
from stock_research.market.bar_service import MarketBarService
from stock_research.quant.factor import FACTOR_POOL


@dataclass(frozen=True)
class FactorValue:
    name: str
    category: str
    value: Decimal | None


def _momentum(closes: list[Decimal], window: int) -> Decimal | None:
    if len(closes) < window + 1:
        return None
    previous = closes[-1 - window]
    if previous == 0:
        return None
    return closes[-1] / previous - Decimal("1")


def _annualized_volatility(closes: list[Decimal], window: int = 20) -> Decimal | None:
    if len(closes) < window + 1:
        return None
    returns = [
        closes[index] / closes[index - 1] - Decimal("1")
        for index in range(len(closes) - window, len(closes))
    ]
    mean = sum(returns, Decimal("0")) / Decimal(len(returns))
    variance = sum(
        (value - mean) ** 2 for value in returns
    ) / Decimal(len(returns))
    return variance.sqrt() * Decimal("252").sqrt()


def _rsi(closes: list[Decimal], period: int = 14) -> Decimal | None:
    if len(closes) < period + 1:
        return None
    gains = Decimal("0")
    losses = Decimal("0")
    for index in range(len(closes) - period, len(closes)):
        change = closes[index] - closes[index - 1]
        if change > 0:
            gains += change
        else:
            losses += -change
    avg_gain = gains / Decimal(period)
    avg_loss = losses / Decimal(period)
    if avg_loss == 0:
        return Decimal("100")
    rs = avg_gain / avg_loss
    return Decimal("100") - Decimal("100") / (Decimal("1") + rs)


def compute_technical_factors(closes: list[Decimal]) -> dict[str, Decimal | None]:
    return {
        "momentum_20": _momentum(closes, 20),
        "momentum_60": _momentum(closes, 60),
        "volatility_20": _annualized_volatility(closes, 20),
        "rsi_14": _rsi(closes, 14),
    }


class FactorPool:
    """聚合投研已有的财务/估值因子与技术/动量因子。"""

    def __init__(self, session: AsyncSession) -> None:
        self._resolver = PitResolver(session)
        self._bar_service = MarketBarService(session)

    async def compute(
        self,
        symbol: str,
        as_of: datetime,
    ) -> list[FactorValue]:
        values: list[FactorValue] = []
        for definition in FACTOR_POOL:
            if definition.source == "fact":
                resolved = await self._resolver.resolve(
                    symbol=symbol,
                    metric=definition.name,
                    as_of=as_of,
                )
                values.append(
                    FactorValue(
                        name=definition.name,
                        category=definition.category,
                        value=resolved.value if resolved is not None else None,
                    )
                )

        bars = await self._bar_service.bars(symbol, "1d", limit=100000, as_of=as_of)
        closes = [Decimal(str(bar.close)) for bar in bars]
        technical = compute_technical_factors(closes)
        for definition in FACTOR_POOL:
            if definition.source == "computed":
                values.append(
                    FactorValue(
                        name=definition.name,
                        category=definition.category,
                        value=technical.get(definition.name),
                    )
                )
        return values
