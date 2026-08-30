from __future__ import annotations

from typing import Protocol

from stock_research.supply_chain.graph_candidate import GraphCandidate


class CypherSession(Protocol):
    def run(self, query: str, **params: object) -> object:
        ...


class Neo4jPublishService:
    """将审核通过的图候选发布为 Neo4j 节点和边。"""

    def publish(
        self,
        session: CypherSession,
        candidate: GraphCandidate,
        evidence_ids: list[str],
    ) -> int:
        for node in candidate.nodes:
            session.run(
                "MERGE (n:Organization {name: $name})",
                name=node,
            )

        edge_count = 0
        for source, predicate, target in candidate.edges:
            session.run(
                """
                MATCH (a:Organization {name: $source})
                MATCH (b:Organization {name: $target})
                MERGE (a)-[r:REL {predicate: $predicate}]->(b)
                SET r.evidence_ids = $evidence_ids
                """,
                source=source,
                target=target,
                predicate=predicate,
                evidence_ids=evidence_ids,
            )
            edge_count += 1
        return edge_count
