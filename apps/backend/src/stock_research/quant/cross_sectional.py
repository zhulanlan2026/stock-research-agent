from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.market.bar_service import MarketBarService
from stock_research.quant.factor_pool import compute_technical_factors, month_end_timestamps
from stock_research.quant.ic import FactorIC, spearman, summarize_ic

TECHNICAL_FACTORS = ("momentum_20", "momentum_60", "volatility_20", "rsi_14")

DEFAULT_UNIVERSE: tuple[str, ...] = (
    "603893.SH", "601869.SH", "301511.SZ", "301183.SZ",
    "300458.SZ", "688099.SH", "688608.SH", "688018.SH",
    "600487.SH", "600522.SH", "600498.SH",
    "600110.SH", "688388.SH", "301150.SZ",
    "002273.SZ", "688127.SH", "002036.SZ",
    "600519.SH", "000858.SZ", "601318.SH", "600036.SH", "000333.SZ",
    "600887.SH", "300750.SZ", "002594.SZ", "601012.SH", "600276.SH",
    "000651.SZ", "601899.SH", "600309.SH",
)


class CrossSectionalICService:
    """在股票池横截面上计算技术因子的月度 IC。"""

    def __init__(self, session: AsyncSession) -> None:
        self._bar_service = MarketBarService(session)

    async def analyze(
        self,
        symbols: list[str],
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        horizon_days: int = 20,
    ) -> list[FactorIC]:
        end = end or datetime.now().astimezone()
        start = start or (end - timedelta(days=730))
        timestamps = month_end_timestamps(start, end)
        if not timestamps:
            return []

        stock_data: dict[str, tuple[list[datetime], list[Decimal]]] = {}
        for symbol in symbols:
            bars = await self._bar_service.bars(symbol, "1d", limit=100000)
            times = [bar.bar_time for bar in bars]
            closes = [Decimal(str(bar.close)) for bar in bars]
            if len(closes) >= 80:
                stock_data[symbol] = (times, closes)

        ic_series: dict[str, list[Decimal]] = {name: [] for name in TECHNICAL_FACTORS}
        for timestamp in timestamps:
            factors: dict[str, list[Decimal]] = {name: [] for name in TECHNICAL_FACTORS}
            returns: list[Decimal] = []
            for _symbol, (times, closes) in stock_data.items():
                index = _index_at_or_before(times, timestamp)
                if index is None or index < 60:
                    continue
                window = closes[index - 60 : index + 1]
                technical = compute_technical_factors(window)
                future_index = _future_index(times, index, horizon_days)
                if future_index is None or closes[index] == 0:
                    continue
                for name in TECHNICAL_FACTORS:
                    value = technical.get(name)
                    if value is not None:
                        factors[name].append(value)
                returns.append(closes[future_index] / closes[index] - Decimal("1"))

            if len(returns) < 3:
                continue
            for name in TECHNICAL_FACTORS:
                if len(factors[name]) == len(returns):
                    ic = spearman(factors[name], returns)
                    if ic is not None:
                        ic_series[name].append(ic)

        results: list[FactorIC] = []
        for name in TECHNICAL_FACTORS:
            summary = summarize_ic(name, ic_series[name])
            if summary is not None:
                results.append(summary)
        return results


def _index_at_or_before(times: list[datetime], target: datetime) -> int | None:
    index = None
    for pos, time in enumerate(times):
        if time <= target:
            index = pos
        else:
            break
    return index


def _future_index(
    times: list[datetime],
    index: int,
    horizon_days: int,
) -> int | None:
    target = times[index] + timedelta(days=horizon_days)
    for pos in range(index + 1, len(times)):
        if times[pos] >= target:
            return pos
    return None
