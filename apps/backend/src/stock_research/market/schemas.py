from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MarketSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    event_time: datetime
    payload: dict[str, object]
    created_at: datetime


class MarketSnapshotSummaryResponse(BaseModel):
    symbol: str
    last_price: float | None
    previous_close: float | None
    change: float | None
    change_pct: float | None
    bid_ask_spread: float | None
    event_time: datetime | None
    sample_count: int


class MarketBarResponse(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None


class MarketIndicatorResponse(BaseModel):
    time: datetime
    ma5: float | None
    ma10: float | None
    ma20: float | None
    ema5: float | None
    ema10: float | None
    ema20: float | None
    volume_ma5: float | None
    volume_ma10: float | None
    macd_dif: float | None
    macd_dea: float | None
    macd_hist: float | None
    rsi: float | None
