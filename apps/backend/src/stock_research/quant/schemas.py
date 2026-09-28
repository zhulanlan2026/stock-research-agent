from datetime import datetime

from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    short_window: int = Field(default=20, ge=2, le=250)
    long_window: int = Field(default=60, ge=2, le=500)


class BacktestMetrics(BaseModel):
    bars: int
    buy_hold_return: float
    strategy_return: float
    annualized_return: float
    max_drawdown: float
    trades: int


class BacktestCurvePoint(BaseModel):
    time: datetime
    equity: float


class BacktestResponse(BaseModel):
    symbol: str
    strategy: str
    short_window: int
    long_window: int
    metrics: BacktestMetrics
    curve: list[BacktestCurvePoint]
