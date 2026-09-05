from decimal import Decimal
from typing import Any

from stock_research.supply_chain.graph_candidate import GraphCandidate
from stock_research.supply_chain.neo4j_rebuild import Neo4jRebuildService
from stock_research.supply_chain.store import SupplyChainStore


class _FakePublisher:
    def __init__(self) -> None:
        self.candidates: list[GraphCandidate] = []
        self.evidence_ids: list[list[str]] = []

    def publish(self, candidate: GraphCandidate, evidence_ids: list[str]) -> int:
        self.candidates.append(candidate)
        self.evidence_ids.append(evidence_ids)
        return len(candidate.edges)


async def test_neo4j_rebuild_builds_candidate_from_contracts(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = SupplyChainStore(session)
        await store.create_contract(
            tenant_id=db_context.tenant_id,
            subject_org="甲公司",
            object_org="乙公司",
            amount=Decimal("100.00"),
            currency="CNY",
            evidence_ids=["ev-1"],
        )
        await store.create_contract(
            tenant_id=db_context.tenant_id,
            subject_org="乙公司",
            object_org="丙公司",
            amount=Decimal("50.00"),
            currency="CNY",
            evidence_ids=["ev-2"],
        )
        await session.commit()

        publisher = _FakePublisher()
        edge_count = await Neo4jRebuildService(session, publisher).rebuild(
            tenant_id=db_context.tenant_id
        )

        assert edge_count == 2
        candidate = publisher.candidates[0]
        assert candidate.nodes == ["甲公司", "乙公司", "丙公司"]
        assert candidate.edges == [
            ("甲公司", "supplies", "乙公司"),
            ("乙公司", "supplies", "丙公司"),
        ]
        assert publisher.evidence_ids[0] == ["ev-1", "ev-2"]
