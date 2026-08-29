from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.peer import PeerComparison, PeerEngine
from stock_research.fundamental.scenario import ScenarioAssumption
from stock_research.fundamental.snapshot import SnapshotEngine, UnifiedSnapshot

STANDARD_RESEARCH_VERSION = "standard_research:1.0.0"


@dataclass(frozen=True)
class StandardResearchResult:
    symbol: str
    as_of: datetime
    module_version: str
    status: str
    snapshot: UnifiedSnapshot
    peer_comparison: PeerComparison | None
    coverage: Decimal


class StandardResearchService:
    """执行一次确定性的标准研究流程。"""

    module_version = STANDARD_RESEARCH_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._snapshot_engine = SnapshotEngine(session)
        self._peer_engine = PeerEngine(session)

    async def run(
        self,
        *,
        symbol: str,
        as_of: datetime,
        scenarios: list[ScenarioAssumption],
        peers: list[str] | None = None,
        price: Decimal | None = None,
    ) -> StandardResearchResult:
        snapshot = await self._snapshot_engine.calculate(
            symbol,
            as_of,
            scenarios,
            price=price,
        )
        peer_comparison = None
        if peers:
            peer_comparison = await self._peer_engine.calculate(
                symbol,
                peers,
                as_of,
            )

        coverage = snapshot.coverage
        if peer_comparison is not None and peers:
            coverage = (coverage + Decimal("1")) / Decimal("2")

        return StandardResearchResult(
            symbol=symbol,
            as_of=as_of,
            module_version=self.module_version,
            status="COMPLETED",
            snapshot=snapshot,
            peer_comparison=peer_comparison,
            coverage=coverage,
        )
