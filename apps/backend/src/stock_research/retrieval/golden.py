from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GoldenQuery:
    query: str
    relevant_doc_ids: frozenset[str]


@dataclass(frozen=True)
class RetrievalEvaluation:
    recall_at_k: float
    mrr: float
    n_dcg: float
    acl_leakage: int
    future_leakage: int = 0


class RetrievalEvaluator:
    """基于 Golden Dataset 计算检索质量。"""

    def evaluate(
        self,
        *,
        queries: list[GoldenQuery],
        ranked_lists: dict[str, list[str]],
        allowed_doc_ids: frozenset[str],
        k: int = 10,
        document_available_at: dict[str, datetime] | None = None,
        as_of: datetime | None = None,
    ) -> RetrievalEvaluation:
        if not queries:
            return RetrievalEvaluation(
                recall_at_k=0.0,
                mrr=0.0,
                n_dcg=0.0,
                acl_leakage=0,
                future_leakage=0,
            )

        recalls: list[float] = []
        reciprocal_ranks: list[float] = []
        ndcgs: list[float] = []
        leakage = 0
        future_leakage = 0

        for item in queries:
            ranked = ranked_lists.get(item.query, [])
            leakage += sum(1 for doc_id in ranked if doc_id not in allowed_doc_ids)
            if document_available_at is not None and as_of is not None:
                for doc_id in ranked:
                    if doc_id not in allowed_doc_ids:
                        continue
                    available_at = document_available_at.get(doc_id)
                    if available_at is not None and available_at > as_of:
                        future_leakage += 1

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
            ndcgs.append(_ndcg(ranked, item.relevant_doc_ids, k))

        return RetrievalEvaluation(
            recall_at_k=sum(recalls) / len(recalls),
            mrr=sum(reciprocal_ranks) / len(reciprocal_ranks),
            n_dcg=sum(ndcgs) / len(ndcgs),
            acl_leakage=leakage,
            future_leakage=future_leakage,
        )


def _ndcg(ranked: list[str], relevant: frozenset[str], k: int) -> float:
    dcg = 0.0
    for index, doc_id in enumerate(ranked[:k], start=1):
        if doc_id in relevant:
            dcg += 1.0 / math.log2(index + 1)
    idcg = 0.0
    for index in range(1, min(k, len(relevant)) + 1):
        idcg += 1.0 / math.log2(index + 1)
    return dcg / idcg if idcg > 0 else 0.0
