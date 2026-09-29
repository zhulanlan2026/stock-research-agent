from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.market.bar_service import MarketBarService
from stock_research.quant.factor_pool import compute_technical_factors
from stock_research.quant.ic import FactorIC, spearman

TECHNICAL_FACTORS = ("momentum_20", "momentum_60", "volatility_20", "rsi_14")


class TimeSeriesICService:
    """用单只股票的日频技术因子与未来收益计算时序 IC。"""

    def __init__(self, session: AsyncSession) -> None:
        self._bar_service = MarketBarService(session)

    async def analyze(
        self,
        symbol: str,
        *,
        horizon: int = 20,
        lookback: int = 60,
    ) -> list[FactorIC]:
        bars = await self._bar_service.bars(symbol, "1d", limit=100000)
        closes = [Decimal(str(bar.close)) for bar in bars]
        if len(closes) < lookback + horizon + 2:
            return []

        series: dict[str, list[Decimal]] = {name: [] for name in TECHNICAL_FACTORS}
        future_returns: list[Decimal] = []
        for index in range(lookback, len(closes) - horizon):
            window = closes[index - lookback : index + 1]
            technical = compute_technical_factors(window)
            for name in TECHNICAL_FACTORS:
                value = technical.get(name)
                if value is not None:
                    series[name].append(value)
            future_returns.append(closes[index + horizon] / closes[index] - Decimal("1"))

        results: list[FactorIC] = []
        for name in TECHNICAL_FACTORS:
            ic = spearman(series[name], future_returns)
            results.append(
                FactorIC(
                    factor=name,
                    observations=len(series[name]),
                    ic_mean=ic,
                    ic_std=None,
                    icir=None,
                    ic_positive_ratio=None,
                )
            )
        return results
