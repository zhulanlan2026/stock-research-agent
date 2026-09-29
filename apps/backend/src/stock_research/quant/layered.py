from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.market.bar_service import MarketBarService
from stock_research.quant.cross_sectional import (
    _future_index,
    _index_at_or_before,
)
from stock_research.quant.factor_pool import compute_technical_factors, month_end_timestamps

TECHNICAL_FACTORS = ("momentum_20", "momentum_60", "volatility_20", "rsi_14")


@dataclass(frozen=True)
class LayeredReturn:
    factor: str
    quantiles: list[Decimal]
    long_short: Decimal


class LayeredReturnService:
    """按因子分 5 组，计算各组平均未来收益与多空收益。"""

    def __init__(self, session: AsyncSession) -> None:
        self._bar_service = MarketBarService(session)

    async def analyze(
        self,
        symbols: list[str],
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        horizon_days: int = 20,
        quantiles: int = 5,
    ) -> list[LayeredReturn]:
        end = end or datetime.now().astimezone()
        start = start or (end - timedelta(days=730))
        timestamps = month_end_timestamps(start, end)

        pairs: dict[str, list[tuple[Decimal, Decimal]]] = {
            name: [] for name in TECHNICAL_FACTORS
        }
        for symbol in symbols:
            bars = await self._bar_service.bars(symbol, "1d", limit=100000)
            times = [bar.bar_time for bar in bars]
            closes = [Decimal(str(bar.close)) for bar in bars]
            if len(closes) < 80:
                continue
            for timestamp in timestamps:
                index = _index_at_or_before(times, timestamp)
                if index is None or index < 60:
                    continue
                technical = compute_technical_factors(closes[index - 60 : index + 1])
                future_index = _future_index(times, index, horizon_days)
                if future_index is None or closes[index] == 0:
                    continue
                future_return = closes[future_index] / closes[index] - Decimal("1")
                for name in TECHNICAL_FACTORS:
                    value = technical.get(name)
                    if value is not None:
                        pairs[name].append((value, future_return))

        results: list[LayeredReturn] = []
        for name in TECHNICAL_FACTORS:
            values = pairs[name]
            if len(values) < quantiles * 2:
                continue
            ordered = sorted(values, key=lambda item: item[0])
            bucket_size = len(ordered) // quantiles
            bucket_returns: list[Decimal] = []
            for bucket in range(quantiles):
                start_index = bucket * bucket_size
                end_index = len(ordered) if bucket == quantiles - 1 else (bucket + 1) * bucket_size
                bucket_values = ordered[start_index:end_index]
                average = sum(item[1] for item in bucket_values) / Decimal(len(bucket_values))
                bucket_returns.append(average)
            results.append(
                LayeredReturn(
                    factor=name,
                    quantiles=bucket_returns,
                    long_short=bucket_returns[-1] - bucket_returns[0],
                )
            )
        return results
