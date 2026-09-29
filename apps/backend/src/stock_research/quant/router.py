from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.market.bar_service import MarketBarService
from stock_research.quant.backtest import run_moving_average_backtest
from stock_research.quant.cross_sectional import (
    DEFAULT_UNIVERSE,
    CrossSectionalICService,
)
from stock_research.quant.factor import FACTOR_POOL
from stock_research.quant.factor_pool import FactorPool, month_end_timestamps
from stock_research.quant.ic_service import TimeSeriesICService
from stock_research.quant.schemas import (
    BacktestCurvePoint,
    BacktestMetrics,
    BacktestRequest,
    BacktestResponse,
    FactorDefinitionResponse,
    FactorHistoryPointResponse,
    FactorHistoryResponse,
    FactorICResponse,
    FactorPoolResponse,
    FactorValueResponse,
)
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session

router = APIRouter(prefix="/backtest", tags=["backtest"])
factors_router = APIRouter(prefix="/factors", tags=["factors"])
ic_router = APIRouter(prefix="/ic", tags=["ic"])


@router.post("", response_model=BacktestResponse)
async def run_backtest(
    body: BacktestRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BacktestResponse:
    bars = await MarketBarService(session).bars(
        body.symbol,
        "1d",
        limit=100000,
    )
    closes = [float(bar.close) for bar in bars]
    times = [bar.bar_time for bar in bars]
    result = run_moving_average_backtest(
        body.symbol,
        times,
        closes,
        short_window=body.short_window,
        long_window=body.long_window,
    )
    return BacktestResponse(
        symbol=result.symbol,
        strategy=result.strategy,
        short_window=result.short_window,
        long_window=result.long_window,
        metrics=BacktestMetrics(
            bars=result.bars,
            buy_hold_return=result.buy_hold_return,
            strategy_return=result.strategy_return,
            annualized_return=result.annualized_return,
            max_drawdown=result.max_drawdown,
            trades=result.trades,
        ),
        curve=[
            BacktestCurvePoint(time=point.time, equity=point.equity)
            for point in result.curve
        ],
    )


@factors_router.get("", response_model=list[FactorDefinitionResponse])
async def list_factors() -> list[FactorDefinitionResponse]:
    return [
        FactorDefinitionResponse(
            name=definition.name,
            category=definition.category,
            description=definition.description,
        )
        for definition in FACTOR_POOL
    ]


@factors_router.get("/{symbol}", response_model=FactorPoolResponse)
async def compute_factors(
    symbol: str,
    as_of: datetime | None = None,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FactorPoolResponse:
    as_of = as_of or datetime.now(timezone.utc)
    values = await FactorPool(session).compute(symbol, as_of)
    return FactorPoolResponse(
        symbol=symbol,
        as_of=as_of,
        factors=[
            FactorValueResponse(
                name=value.name,
                category=value.category,
                value=value.value,
            )
            for value in values
        ],
    )


@factors_router.get("/{symbol}/history", response_model=FactorHistoryResponse)
async def compute_factor_history(
    symbol: str,
    start: datetime | None = None,
    end: datetime | None = None,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FactorHistoryResponse:
    end_dt = end or datetime.now(timezone.utc)
    start_dt = start or (end_dt - timedelta(days=730))
    timestamps = month_end_timestamps(start_dt, end_dt)
    points = await FactorPool(session).compute_history(symbol, timestamps)
    return FactorHistoryResponse(
        symbol=symbol,
        points=[
            FactorHistoryPointResponse(
                as_of=point.as_of,
                factors=[
                    FactorValueResponse(
                        name=value.name,
                        category=value.category,
                        value=value.value,
                    )
                    for value in point.factors
                ],
            )
            for point in points
        ],
    )


@ic_router.get("/cross-sectional", response_model=list[FactorICResponse])
async def compute_cross_sectional_ic(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[FactorICResponse]:
    results = await CrossSectionalICService(session).analyze(list(DEFAULT_UNIVERSE))
    return [
        FactorICResponse(
            factor=result.factor,
            observations=result.observations,
            ic_mean=result.ic_mean,
            ic_std=result.ic_std,
            icir=result.icir,
            ic_positive_ratio=result.ic_positive_ratio,
        )
        for result in results
    ]


@ic_router.get("/{symbol}", response_model=list[FactorICResponse])
async def compute_ic(
    symbol: str,
    horizon: int = 20,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[FactorICResponse]:
    results = await TimeSeriesICService(session).analyze(symbol, horizon=horizon)
    return [
        FactorICResponse(
            factor=result.factor,
            observations=result.observations,
            ic_mean=result.ic_mean,
            ic_std=result.ic_std,
            icir=result.icir,
            ic_positive_ratio=result.ic_positive_ratio,
        )
        for result in results
    ]
