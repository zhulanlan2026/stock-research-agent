from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.supply_chain.graph_candidate import GraphCandidate
from stock_research.supply_chain.store import SupplyChainStore


class GraphPublisher(Protocol):
    def publish(self, candidate: GraphCandidate, evidence_ids: list[str]) -> int:
        ...


class Neo4jRebuildService:
    """从 PostgreSQL 供应链数据重建 Neo4j 图。"""

    def __init__(self, session: AsyncSession, publisher: GraphPublisher) -> None:
        self.session = session
        self.publisher = publisher

    async def rebuild(self, *, tenant_id: uuid.UUID | None = None) -> int:
        contracts = await SupplyChainStore(self.session).list_contracts(
            tenant_id=tenant_id
        )
        nodes: list[str] = []
        edges: list[tuple[str, str, str]] = []
        evidence_ids: list[str] = []
        for contract in contracts:
            if contract.subject_org not in nodes:
                nodes.append(contract.subject_org)
            if contract.object_org not in nodes:
                nodes.append(contract.object_org)
            edges.append((contract.subject_org, "supplies", contract.object_org))
            evidence_ids.extend(contract.evidence_ids)

        if not edges:
            return 0

        candidate = GraphCandidate(nodes=nodes, edges=edges)
        return self.publisher.publish(candidate, evidence_ids)
