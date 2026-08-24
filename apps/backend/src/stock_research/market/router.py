from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.iam.dependencies import require_permission
from stock_research.market.analysis import MarketAnalysisService
from stock_research.market.bar_service import MarketBarService
from stock_research.market.indicators import IndicatorService
from stock_research.market.schemas import (
    MarketBarResponse,
    MarketIndicatorResponse,
    MarketSnapshotResponse,
    MarketSnapshotSummaryResponse,
)
from stock_research.market.store import MarketSnapshotStore
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session

router = APIRouter(prefix="/market", tags=["market"])
_require_market_read = require_permission("stock.market.read")


@router.get("/snapshots/{symbol}", response_model=list[MarketSnapshotResponse])
async def list_market_snapshots(
    symbol: str = Path(min_length=1, max_length=32),
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(_require_market_read),
    session: AsyncSession = Depends(get_session),
) -> list[MarketSnapshotResponse]:
    snapshots = await MarketSnapshotStore(session).latest(symbol, limit)
    return [MarketSnapshotResponse.model_validate(snapshot) for snapshot in snapshots]


@router.get(
    "/snapshots/{symbol}/summary",
    response_model=MarketSnapshotSummaryResponse,
)
async def market_snapshot_summary(
    symbol: str = Path(min_length=1, max_length=32),
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(_require_market_read),
    session: AsyncSession = Depends(get_session),
) -> MarketSnapshotSummaryResponse:
    summary = await MarketAnalysisService(session).summarize(symbol, limit)
    return MarketSnapshotSummaryResponse(
        symbol=summary.symbol,
        last_price=summary.last_price,
        previous_close=summary.previous_close,
        change=summary.change,
        change_pct=summary.change_pct,
        bid_ask_spread=summary.bid_ask_spread,
        event_time=summary.event_time,
        sample_count=summary.sample_count,
    )


@router.get("/bars/{symbol}", response_model=list[MarketBarResponse])
async def list_market_bars(
    symbol: str = Path(min_length=1, max_length=32),
    period: str = Query(default="1m", pattern="^(1m|5m|15m|30m|1h|1d)$"),
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(_require_market_read),
    session: AsyncSession = Depends(get_session),
) -> list[MarketBarResponse]:
    bars = await MarketBarService(session).bars(symbol, period, limit)
    return [
        MarketBarResponse(
            time=bar.bar_time,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
        for bar in bars
    ]


@router.get(
    "/bars/{symbol}/indicators",
    response_model=list[MarketIndicatorResponse],
)
async def list_market_indicators(
    symbol: str = Path(min_length=1, max_length=32),
    period: str = Query(default="1m", pattern="^(1m|5m|15m|30m|1h|1d)$"),
    limit: int = Query(default=100, ge=1, le=500),
    rsi_period: int = Query(default=14, ge=2, le=100),
    macd_fast: int = Query(default=12, ge=2, le=100),
    macd_slow: int = Query(default=26, ge=2, le=200),
    macd_signal: int = Query(default=9, ge=2, le=100),
    _: User = Depends(_require_market_read),
    session: AsyncSession = Depends(get_session),
) -> list[MarketIndicatorResponse]:
    points = await IndicatorService(session).indicators(
        symbol,
        period,
        limit,
        rsi_period=rsi_period,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
    )
    return [
        MarketIndicatorResponse(
            time=point.time,
            ma5=point.ma5,
            ma10=point.ma10,
            ma20=point.ma20,
            ema5=point.ema5,
            ema10=point.ema10,
            ema20=point.ema20,
            volume_ma5=point.volume_ma5,
            volume_ma10=point.volume_ma10,
            macd_dif=point.macd_dif,
            macd_dea=point.macd_dea,
            macd_hist=point.macd_hist,
            rsi=point.rsi,
        )
        for point in points
    ]
