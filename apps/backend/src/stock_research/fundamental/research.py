from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.peer import PeerComparison, PeerEngine
from stock_research.fundamental.pit import PitResolver
from stock_research.fundamental.scenario import ScenarioAssumption
from stock_research.fundamental.snapshot import SnapshotEngine, UnifiedSnapshot

STANDARD_RESEARCH_VERSION = "standard_research:1.0.0"

DEFAULT_SCENARIOS = (
    ScenarioAssumption(name="BASE", pe=Decimal("20")),
    ScenarioAssumption(name="BULL", pe=Decimal("28")),
    ScenarioAssumption(name="BEAR", pe=Decimal("14")),
)

SYMBOL_TO_PEERS: dict[str, tuple[str, ...]] = {
    "603893.SH": ("300458.SZ", "688099.SH", "688608.SH", "688018.SH"),
    "601869.SH": ("600487.SH", "600522.SH", "600498.SH"),
    "301511.SZ": ("600110.SH", "688388.SH", "301150.SZ"),
    "301183.SZ": ("002273.SZ", "688127.SH", "002036.SZ"),
}


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
        self._pit_resolver = PitResolver(session)

    async def run(
        self,
        *,
        symbol: str,
        as_of: datetime,
        scenarios: list[ScenarioAssumption],
        peers: list[str] | None = None,
        price: Decimal | None = None,
    ) -> StandardResearchResult:
        scenarios = await self._market_pe_scenarios(symbol, as_of, scenarios)
        effective_peers = peers if peers is not None else list(
            SYMBOL_TO_PEERS.get(symbol, ())
        )
        snapshot = await self._snapshot_engine.calculate(
            symbol,
            as_of,
            scenarios,
            price=price,
        )
        peer_comparison = None
        if effective_peers:
            peer_comparison = await self._peer_engine.calculate(
                symbol,
                effective_peers,
                as_of,
            )

        coverage = snapshot.coverage
        if peer_comparison is not None and effective_peers:
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

    async def _market_pe_scenarios(
        self,
        symbol: str,
        as_of: datetime,
        scenarios: list[ScenarioAssumption],
    ) -> list[ScenarioAssumption]:
        resolved = await self._pit_resolver.resolve(
            symbol=symbol,
            metric="pe_ttm",
            as_of=as_of,
        )
        if resolved is None or resolved.value <= 0:
            return scenarios
        base_pe = resolved.value
        return [
            ScenarioAssumption(name="BASE", pe=base_pe),
            ScenarioAssumption(name="BULL", pe=base_pe * Decimal("1.4")),
            ScenarioAssumption(name="BEAR", pe=base_pe * Decimal("0.6")),
        ]
