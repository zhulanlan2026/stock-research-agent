from __future__ import annotations

from typing import Protocol

from stock_research.retrieval.bm25 import BM25Index
from stock_research.retrieval.rrf import ReciprocalRankFusion


class DenseSearchable(Protocol):
    def search(
        self, query: list[float], top_k: int = 10
    ) -> list[tuple[str, float]]:
        ...


class HybridRetrievalPipeline:
    """混合检索装配入口：BM25 + Dense + RRF。"""

    def __init__(
        self,
        *,
        bm25: BM25Index,
        dense: DenseSearchable,
    ) -> None:
        self._bm25 = bm25
        self._dense = dense

    def retrieve(
        self,
        query: str,
        query_vector: list[float],
        *,
        top_k: int = 10,
        rrf_k: int = 60,
    ) -> list[str]:
        bm25_ranked = [
            doc_id for doc_id, _ in self._bm25.search(query, top_k=top_k)
        ]
        dense_ranked = [
            doc_id for doc_id, _ in self._dense.search(query_vector, top_k=top_k)
        ]
        fused = ReciprocalRankFusion().fuse(
            [bm25_ranked, dense_ranked], k=rrf_k
        )
        return [doc_id for doc_id, _ in fused[:top_k]]
