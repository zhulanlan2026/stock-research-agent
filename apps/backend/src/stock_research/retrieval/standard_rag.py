from __future__ import annotations

from dataclasses import dataclass

from stock_research.retrieval.bm25 import BM25Index


@dataclass(frozen=True)
class StandardRagEvidence:
    evidence_id: str
    content: str


class StandardRagService:
    """基于 Evidence 内容的确定性标准 RAG 检索入口。"""

    def __init__(self, evidence: list[StandardRagEvidence]) -> None:
        self._evidence = {item.evidence_id: item.content for item in evidence}
        self._bm25 = BM25Index()
        for evidence_id, content in self._evidence.items():
            self._bm25.add_document(evidence_id, content)

    def retrieve(self, query: str, *, top_k: int = 10) -> list[str]:
        return [
            evidence_id
            for evidence_id, _score in self._bm25.search(query, top_k=top_k)
        ]
