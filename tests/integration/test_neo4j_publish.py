import pytest

from stock_research.supply_chain.graph_candidate import GraphCandidate
from stock_research.supply_chain.neo4j_client import Neo4jPublisher


def test_neo4j_publisher_writes_graph() -> None:
    publisher = Neo4jPublisher("bolt://localhost:7687", "neo4j", "password123")
    try:
        try:
            publisher._driver.verify_connectivity()
        except Exception as exc:  # pragma: no cover - environment-dependent
            publisher.close()
            pytest.skip(f"Neo4j unavailable: {exc}")

        candidate = GraphCandidate(
            nodes=["甲公司", "乙公司"],
            edges=[("甲公司", "supplies", "乙公司")],
        )
        edge_count = publisher.publish(candidate, ["ev-1"])

        assert edge_count == 1
    finally:
        publisher.close()
