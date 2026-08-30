from stock_research.supply_chain.graph_candidate import GraphCandidate
from stock_research.supply_chain.neo4j_publisher import Neo4jPublishService


class _FakeSession:
    def __init__(self) -> None:
        self.queries: list[tuple[str, dict[str, object]]] = []

    def run(self, query: str, **params: object) -> object:
        self.queries.append((query, params))
        return object()


def test_neo4j_publish_service_merges_nodes_and_edges() -> None:
    session = _FakeSession()
    candidate = GraphCandidate(nodes=["A", "B"], edges=[("A", "edge", "B")])

    count = Neo4jPublishService().publish(session, candidate, ["evidence-1"])

    assert count == 1
    assert len(session.queries) == 3
    assert "MERGE (n:Organization" in session.queries[0][0]
    assert "MERGE (a)-[r:REL" in session.queries[2][0]
