from __future__ import annotations

import math


class DenseIndex:
    """轻量稠密向量索引，按余弦相似度排序。"""

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}

    def add(self, vector_id: str, vector: list[float]) -> None:
        if not vector:
            raise ValueError("vector must not be empty")
        self._vectors[vector_id] = list(vector)

    def search(self, query: list[float], top_k: int = 10) -> list[tuple[str, float]]:
        if not query:
            raise ValueError("query must not be empty")
        scored: list[tuple[str, float]] = []
        for vector_id, vector in self._vectors.items():
            score = _cosine(query, vector)
            if score is not None:
                scored.append((vector_id, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


def _cosine(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right):
        return None
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return None
    return dot / (left_norm * right_norm)
