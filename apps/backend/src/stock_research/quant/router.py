from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.market.bar_service import MarketBarService
from stock_research.quant.backtest import run_moving_average_backtest
from stock_research.quant.schemas import (
    BacktestCurvePoint,
    BacktestMetrics,
    BacktestRequest,
    BacktestResponse,
)
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session

router = APIRouter(prefix="/backtest", tags=["backtest"])


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
