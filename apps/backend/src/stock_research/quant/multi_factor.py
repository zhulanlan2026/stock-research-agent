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

# 因子方向与权重：1 表示越高越好，-1 表示反转（越低越好）。
FACTOR_CONFIG: tuple[tuple[str, int, float], ...] = (
    ("momentum_20", 1, 1.0),
    ("momentum_60", -1, 1.0),
    ("volatility_20", -1, 1.0),
    ("rsi_14", -1, 1.0),
)


@dataclass(frozen=True)
class MultiFactorResult:
    periods: int
    portfolio_return: float
    portfolio_annualized: float
    portfolio_max_drawdown: float
    benchmark_return: float
    benchmark_annualized: float


def _zscore(values: list[Decimal]) -> list[Decimal]:
    mean = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values))
    std = variance.sqrt()
    if std == 0:
        return [Decimal("0") for _ in values]
    return [(value - mean) / std for value in values]


class MultiFactorService:
    """横截面多因子打分选股并回测。"""

    def __init__(self, session: AsyncSession) -> None:
        self._bar_service = MarketBarService(session)

    async def backtest(
        self,
        symbols: list[str],
        *,
        top_n: int = 10,
        horizon_days: int = 20,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> MultiFactorResult:
        end = end or datetime.now().astimezone()
        start = start or (end - timedelta(days=730))
        timestamps = month_end_timestamps(start, end)

        stock_data: dict[str, tuple[list[datetime], list[Decimal]]] = {}
        for symbol in symbols:
            bars = await self._bar_service.bars(symbol, "1d", limit=100000)
            times = [bar.bar_time for bar in bars]
            closes = [Decimal(str(bar.close)) for bar in bars]
            if len(closes) >= 80:
                stock_data[symbol] = (times, closes)

        portfolio_returns: list[Decimal] = []
        benchmark_returns: list[Decimal] = []
        for timestamp in timestamps:
            rows: dict[str, tuple[dict[str, Decimal], Decimal]] = {}
            for symbol, (times, closes) in stock_data.items():
                index = _index_at_or_before(times, timestamp)
                if index is None or index < 60:
                    continue
                technical = compute_technical_factors(closes[index - 60 : index + 1])
                future_index = _future_index(times, index, horizon_days)
                if future_index is None or closes[index] == 0:
                    continue
                factor_values: dict[str, Decimal] = {}
                for name in TECHNICAL_FACTORS:
                    value = technical.get(name)
                    if value is not None:
                        factor_values[name] = value
                future_return = closes[future_index] / closes[index] - Decimal("1")
                rows[symbol] = (factor_values, future_return)

            if len(rows) < top_n:
                continue

            scores: dict[str, Decimal] = {symbol: Decimal("0") for symbol in rows}
            for factor, direction, weight in FACTOR_CONFIG:
                values = [
                    rows[symbol][0][factor]
                    for symbol in rows
                    if factor in rows[symbol][0]
                ]
                if len(values) != len(rows):
                    continue
                zscores = _zscore(values)
                for (symbol, zscore) in zip(rows, zscores, strict=True):
                    scores[symbol] += Decimal(direction) * Decimal(str(weight)) * zscore

            ranked = sorted(rows, key=lambda symbol: scores[symbol], reverse=True)
            selected = ranked[:top_n]
            portfolio_returns.append(
                sum(rows[symbol][1] for symbol in selected) / Decimal(len(selected))
            )
            benchmark_returns.append(
                sum(rows[symbol][1] for symbol in rows) / Decimal(len(rows))
            )

        portfolio_equity = _cumulative(portfolio_returns)
        benchmark_equity = _cumulative(benchmark_returns)
        years = Decimal(len(portfolio_returns)) / Decimal("12")
        return MultiFactorResult(
            periods=len(portfolio_returns),
            portfolio_return=float(portfolio_equity - Decimal("1")),
            portfolio_annualized=float(
                portfolio_equity ** (Decimal("1") / years) - Decimal("1")
                if years > 0 and portfolio_equity > 0 else Decimal("0")
            ),
            portfolio_max_drawdown=float(_max_drawdown(portfolio_returns)),
            benchmark_return=float(benchmark_equity - Decimal("1")),
            benchmark_annualized=float(
                benchmark_equity ** (Decimal("1") / years) - Decimal("1")
                if years > 0 and benchmark_equity > 0 else Decimal("0")
            ),
        )


def _cumulative(returns: list[Decimal]) -> Decimal:
    equity = Decimal("1")
    for value in returns:
        equity *= Decimal("1") + value
    return equity


def _max_drawdown(returns: list[Decimal]) -> Decimal:
    equity = Decimal("1")
    peak = Decimal("1")
    max_drawdown = Decimal("0")
    for value in returns:
        equity *= Decimal("1") + value
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak if peak > 0 else Decimal("0")
        max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown
