from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.market.analysis import MarketAnalysisService, MarketSnapshotSummary
from stock_research.market.indicators import IndicatorPoint, IndicatorService

TECHNICAL_ENGINE_VERSION = "technical:1.0.0"
MARKET_ENGINE_VERSION = "market:1.0.0"


@dataclass(frozen=True)
class TechnicalEngineResult:
    symbol: str
    period: str
    as_of: datetime
    module_version: str
    data_versions: dict[str, object]
    points: list[IndicatorPoint]


@dataclass(frozen=True)
class MarketEngineResult:
    symbol: str
    as_of: datetime
    module_version: str
    data_versions: dict[str, object]
    summary: MarketSnapshotSummary


class TechnicalEngine:
    """确定性技术指标计算引擎，同一输入和版本必须产生同一正式结果。"""

    module_version = TECHNICAL_ENGINE_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._indicator_service = IndicatorService(session)

    async def calculate(
        self,
        symbol: str,
        period: str = "1m",
        limit: int = 100,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
    ) -> TechnicalEngineResult:
        points = await self._indicator_service.indicators(
            symbol,
            period,
            limit,
            rsi_period=rsi_period,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
        )
        as_of = points[-1].time if points else datetime.now(timezone.utc)
        return TechnicalEngineResult(
            symbol=symbol,
            period=period,
            as_of=as_of,
            module_version=self.module_version,
            data_versions={"source": "postgresql", "as_of": as_of.isoformat()},
            points=points,
        )


class MarketEngine:
    """确定性行情摘要引擎，禁止由 LLM 直接产正式行情数字。"""

    module_version = MARKET_ENGINE_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._analysis_service = MarketAnalysisService(session)

    async def calculate(self, symbol: str, limit: int = 20) -> MarketEngineResult:
        summary = await self._analysis_service.summarize(symbol, limit)
        as_of = summary.event_time or datetime.now(timezone.utc)
        return MarketEngineResult(
            symbol=symbol,
            as_of=as_of,
            module_version=self.module_version,
            data_versions={"source": "postgresql", "as_of": as_of.isoformat()},
            summary=summary,
        )
