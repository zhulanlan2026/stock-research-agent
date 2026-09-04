from __future__ import annotations

from typing import Any

from neo4j import Driver, GraphDatabase, Session

from stock_research.supply_chain.graph_candidate import GraphCandidate
from stock_research.supply_chain.neo4j_publisher import Neo4jPublishService


class _SessionAdapter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def run(self, query: str, **params: Any) -> object:
        return self._session.run(query, **params)


class Neo4jPublisher:
    """连接真实 Neo4j，发布审核通过的图候选。"""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def publish(self, candidate: GraphCandidate, evidence_ids: list[str]) -> int:
        with self._driver.session() as session:
            return Neo4jPublishService().publish(
                _SessionAdapter(session), candidate, evidence_ids
            )

    def close(self) -> None:
        self._driver.close()
