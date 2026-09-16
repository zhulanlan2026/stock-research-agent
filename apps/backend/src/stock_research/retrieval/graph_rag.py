from __future__ import annotations

import math
import re
from dataclasses import dataclass

from stock_research.supply_chain.neo4j_client import GraphData

TOKEN_RE = re.compile(r"[a-zA-Z0-9_\u4e00-\u9fff]+")


@dataclass(frozen=True)
class GraphEvidence:
    source: str
    predicate: str
    target: str
    score: float


class GraphRagRetriever:
    """基于 Neo4j 供应链图的确定性 Graph RAG 检索器。"""

    def __init__(self, graph: GraphData) -> None:
        self._graph = graph

    def retrieve(self, query: str, *, top_k: int = 10) -> list[GraphEvidence]:
        query_tokens = set(_tokenize(query))
        if not query_tokens:
            return []

        scored: list[GraphEvidence] = []
        for source, predicate, target in self._graph.edges:
            text = f"{source} {predicate} {target}"
            score = _overlap(query_tokens, _tokenize(text))
            if score > 0:
                scored.append(
                    GraphEvidence(
                        source=source,
                        predicate=predicate,
                        target=target,
                        score=score,
                    )
                )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _overlap(query_tokens: set[str], text_tokens: list[str]) -> float:
    if not text_tokens:
        return 0.0
    hits = sum(1 for token in query_tokens if token in text_tokens)
    return hits / math.sqrt(len(query_tokens) * len(text_tokens))
