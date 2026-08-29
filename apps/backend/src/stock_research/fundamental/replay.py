from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.risk import RiskEngine, RiskSnapshot

RISK_REPLAY_VERSION = "risk_replay:1.0.0"


@dataclass(frozen=True)
class RiskReplayResult:
    symbol: str
    module_version: str
    points: list[RiskSnapshot]


class RiskReplayService:
    """按多个 as_of 时点回放风险快照，验证 PIT 可复现性。"""

    module_version = RISK_REPLAY_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._risk_engine = RiskEngine(session)

    async def replay(
        self,
        symbol: str,
        as_of_points: list[datetime],
        period: str = "1d",
        limit: int = 252,
    ) -> RiskReplayResult:
        points = [
            await self._risk_engine.calculate(
                symbol,
                as_of,
                period=period,
                limit=limit,
            )
            for as_of in as_of_points
        ]
        return RiskReplayResult(
            symbol=symbol,
            module_version=self.module_version,
            points=points,
        )
