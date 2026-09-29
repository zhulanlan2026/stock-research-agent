from datetime import datetime
from decimal import Decimal

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


class FactorDefinitionResponse(BaseModel):
    name: str
    category: str
    description: str


class FactorValueResponse(BaseModel):
    name: str
    category: str
    value: Decimal | None


class FactorPoolResponse(BaseModel):
    symbol: str
    as_of: datetime
    factors: list[FactorValueResponse]


class FactorHistoryPointResponse(BaseModel):
    as_of: datetime
    factors: list[FactorValueResponse]


class FactorHistoryResponse(BaseModel):
    symbol: str
    points: list[FactorHistoryPointResponse]


class FactorICResponse(BaseModel):
    factor: str
    observations: int
    ic_mean: Decimal | None
    ic_std: Decimal | None
    icir: Decimal | None
    ic_positive_ratio: Decimal | None


class LayeredReturnResponse(BaseModel):
    factor: str
    quantiles: list[Decimal]
    long_short: Decimal
