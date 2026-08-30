from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenQuery:
    query: str
    relevant_doc_ids: frozenset[str]


@dataclass(frozen=True)
class RetrievalEvaluation:
    recall_at_k: float
    mrr: float
    acl_leakage: int


class RetrievalEvaluator:
    """基于 Golden Dataset 计算检索质量。"""

    def evaluate(
        self,
        *,
        queries: list[GoldenQuery],
        ranked_lists: dict[str, list[str]],
        allowed_doc_ids: frozenset[str],
        k: int = 10,
    ) -> RetrievalEvaluation:
        if not queries:
            return RetrievalEvaluation(recall_at_k=0.0, mrr=0.0, acl_leakage=0)

        recalls: list[float] = []
        reciprocal_ranks: list[float] = []
        leakage = 0

        for item in queries:
            ranked = ranked_lists.get(item.query, [])
            leakage += sum(1 for doc_id in ranked if doc_id not in allowed_doc_ids)

            top_k = ranked[:k]
            hits = sum(1 for doc_id in top_k if doc_id in item.relevant_doc_ids)
            total_relevant = len(item.relevant_doc_ids)
            recalls.append(hits / total_relevant if total_relevant else 1.0)

            reciprocal_rank = 0.0
            for rank, doc_id in enumerate(ranked, start=1):
                if doc_id in item.relevant_doc_ids:
                    reciprocal_rank = 1 / rank
                    break
            reciprocal_ranks.append(reciprocal_rank)

        return RetrievalEvaluation(
            recall_at_k=sum(recalls) / len(recalls),
            mrr=sum(reciprocal_ranks) / len(reciprocal_ranks),
            acl_leakage=leakage,
        )
