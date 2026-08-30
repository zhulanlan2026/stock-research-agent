from __future__ import annotations

from collections import defaultdict


class ReciprocalRankFusion:
    """对多路排序列表执行 RRF 融合。"""

    def fuse(
        self,
        ranked_lists: list[list[str]],
        *,
        k: int = 60,
    ) -> list[tuple[str, float]]:
        scores: dict[str, float] = defaultdict(float)
        for ranked in ranked_lists:
            for rank, doc_id in enumerate(ranked, start=1):
                scores[doc_id] += 1 / (k + rank)
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return ordered
