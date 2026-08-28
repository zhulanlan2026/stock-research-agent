"""Deterministic peer-group comparison engine.

C2-005 "Peer" is interpreted here as a reproducible comparison against a
caller-supplied peer list. The engine reuses the deterministic fundamental
snapshots and only computes comparison facts; it never invents financial
numbers or rankings from an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.fundamental.engine import FundamentalEngine, FundamentalSnapshot

PEER_ENGINE_VERSION = "peer:1.0.0"


@dataclass(frozen=True)
class PeerComparison:
    symbol: str
    as_of: datetime
    module_version: str
    subject: FundamentalSnapshot
    peers: dict[str, FundamentalSnapshot]
    peer_ranks: dict[str, Decimal | None]


class PeerEngine:
    """基于确定性 FundamentalEngine 生成同业可比快照。"""

    module_version = PEER_ENGINE_VERSION

    def __init__(self, session: AsyncSession) -> None:
        self._fundamental_engine = FundamentalEngine(session)

    async def calculate(
        self,
        symbol: str,
        peers: list[str],
        as_of: datetime,
    ) -> PeerComparison:
        subject = await self._fundamental_engine.calculate(symbol, as_of)
        peer_snapshots = {
            peer: await self._fundamental_engine.calculate(peer, as_of)
            for peer in peers
        }
        return PeerComparison(
            symbol=symbol,
            as_of=as_of,
            module_version=self.module_version,
            subject=subject,
            peers=peer_snapshots,
            peer_ranks=_compute_peer_ranks(subject, peer_snapshots),
        )


def _compute_peer_ranks(
    subject: FundamentalSnapshot,
    peers: dict[str, FundamentalSnapshot],
) -> dict[str, Decimal | None]:
    return {
        ratio_key: _peer_rank(
            subject.ratios.get(ratio_key),
            [peer.ratios.get(ratio_key) for peer in peers.values()],
        )
        for ratio_key in subject.ratios
    }


def _peer_rank(
    subject_value: Decimal | None,
    peer_values: list[Decimal | None],
) -> Decimal | None:
    if subject_value is None:
        return None
    values = [value for value in peer_values if value is not None]
    if not values:
        return None
    below = sum(1 for value in values if value < subject_value)
    return Decimal(below) / Decimal(len(values))
