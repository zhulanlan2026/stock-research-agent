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
    top_n: int
    periods: int
    portfolio_return: float
    portfolio_annualized: float
    portfolio_max_drawdown: float
    benchmark_return: float
    benchmark_annualized: float


@dataclass(frozen=True)
class PeriodResult:
    timestamp: datetime
    selected: tuple[str, ...]
    portfolio_return: Decimal
    benchmark_return: Decimal
    turnover: Decimal


@dataclass(frozen=True)
class SampleSplitResult:
    top_n: int
    in_sample_periods: int
    in_sample_return: float
    out_sample_periods: int
    out_sample_return: float


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
        cost_rate: float = 0.0,
    ) -> MultiFactorResult:
        periods = await self._collect_periods(
            symbols,
            top_n=top_n,
            horizon_days=horizon_days,
            start=start,
            end=end,
        )
        returns = [
            period.portfolio_return - period.turnover * Decimal("2") * Decimal(str(cost_rate))
            for period in periods
        ]
        benchmark_returns = [period.benchmark_return for period in periods]
        portfolio_equity = _cumulative(returns)
        benchmark_equity = _cumulative(benchmark_returns)
        years = Decimal(len(returns)) / Decimal("12")
        return MultiFactorResult(
            top_n=top_n,
            periods=len(returns),
            portfolio_return=float(portfolio_equity - Decimal("1")),
            portfolio_annualized=float(
                portfolio_equity ** (Decimal("1") / years) - Decimal("1")
                if years > 0 and portfolio_equity > 0 else Decimal("0")
            ),
            portfolio_max_drawdown=float(_max_drawdown(returns)),
            benchmark_return=float(benchmark_equity - Decimal("1")),
            benchmark_annualized=float(
                benchmark_equity ** (Decimal("1") / years) - Decimal("1")
                if years > 0 and benchmark_equity > 0 else Decimal("0")
            ),
        )

    async def out_of_sample(
        self,
        symbols: list[str],
        *,
        top_n: int = 10,
        horizon_days: int = 20,
        start: datetime | None = None,
        end: datetime | None = None,
        split_ratio: float = 0.6,
        cost_rate: float = 0.0,
    ) -> SampleSplitResult:
        periods = await self._collect_periods(
            symbols,
            top_n=top_n,
            horizon_days=horizon_days,
            start=start,
            end=end,
        )
        split_index = int(len(periods) * split_ratio)
        in_sample = periods[:split_index]
        out_sample = periods[split_index:]

        def net_return(part: list[PeriodResult]) -> float:
            equity = Decimal("1")
            for period in part:
                cost = period.turnover * Decimal("2") * Decimal(str(cost_rate))
                net = period.portfolio_return - cost
                equity *= Decimal("1") + net
            return float(equity - Decimal("1"))

        return SampleSplitResult(
            top_n=top_n,
            in_sample_periods=len(in_sample),
            in_sample_return=net_return(in_sample),
            out_sample_periods=len(out_sample),
            out_sample_return=net_return(out_sample),
        )

    async def parameter_sweep(
        self,
        symbols: list[str],
        *,
        top_n_values: list[int],
        horizon_days: int = 20,
        start: datetime | None = None,
        end: datetime | None = None,
        cost_rate: float = 0.0,
    ) -> list[MultiFactorResult]:
        results: list[MultiFactorResult] = []
        for top_n in top_n_values:
            result = await self.backtest(
                symbols,
                top_n=top_n,
                horizon_days=horizon_days,
                start=start,
                end=end,
                cost_rate=cost_rate,
            )
            results.append(result)
        return results

    async def _collect_periods(
        self,
        symbols: list[str],
        *,
        top_n: int,
        horizon_days: int,
        start: datetime | None,
        end: datetime | None,
    ) -> list[PeriodResult]:
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

        periods: list[PeriodResult] = []
        previous_selected: set[str] = set()
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
            selected_set = set(selected)
            turnover = (
                Decimal(len(previous_selected ^ selected_set)) / Decimal(len(selected))
                if previous_selected else Decimal("1")
            )
            periods.append(
                PeriodResult(
                    timestamp=timestamp,
                    selected=tuple(selected),
                    portfolio_return=(
                        sum(rows[symbol][1] for symbol in selected) / Decimal(len(selected))
                    ),
                    benchmark_return=sum(rows[symbol][1] for symbol in rows) / Decimal(len(rows)),
                    turnover=turnover,
                )
            )
            previous_selected = selected_set

        return periods


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
