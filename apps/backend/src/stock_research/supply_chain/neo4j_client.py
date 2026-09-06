from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neo4j import Driver, GraphDatabase, Session

from stock_research.supply_chain.graph_candidate import GraphCandidate
from stock_research.supply_chain.neo4j_publisher import Neo4jPublishService


class _SessionAdapter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def run(self, query: str, **params: Any) -> object:
        return self._session.run(query, **params)


@dataclass(frozen=True)
class GraphData:
    nodes: list[str]
    edges: list[tuple[str, str, str]]  # (source, predicate, target)


class Neo4jPublisher:
    """连接真实 Neo4j，发布审核通过的图候选。"""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def publish(self, candidate: GraphCandidate, evidence_ids: list[str]) -> int:
        with self._driver.session() as session:
            return Neo4jPublishService().publish(
                _SessionAdapter(session), candidate, evidence_ids
            )

    def list_graph(self) -> GraphData:
        with self._driver.session() as session:
            nodes_result = session.run(
                "MATCH (n:Organization) RETURN n.name AS name ORDER BY n.name"
            )
            nodes = [record["name"] for record in nodes_result]
            edges_result = session.run(
                "MATCH (a:Organization)-[r:REL]->(b:Organization) "
                "RETURN a.name AS source, r.predicate AS predicate, b.name AS target"
            )
            edges = [
                (record["source"], record["predicate"], record["target"])
                for record in edges_result
            ]
        return GraphData(nodes=nodes, edges=edges)

    def close(self) -> None:
        self._driver.close()
