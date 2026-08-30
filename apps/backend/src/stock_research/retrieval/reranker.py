from __future__ import annotations

import math
import re
from dataclasses import dataclass

TOKEN_RE = re.compile(r"[a-zA-Z0-9_\u4e00-\u9fff]+")


@dataclass(frozen=True)
class RerankCandidate:
    doc_id: str
    text: str
    authority_score: float = 0.0
    age_days: float | None = None


class LexicalReranker:
    """确定性词法重排器，组合查询重叠、权威分和新鲜度。"""

    def rerank(
        self,
        candidates: list[RerankCandidate],
        query: str,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[str, float]] = []
        for candidate in candidates:
            text_tokens = _tokenize(candidate.text)
            score = _overlap_score(query_tokens, text_tokens)
            score += candidate.authority_score * 0.1
            if candidate.age_days is not None:
                score += 0.1 / (1 + candidate.age_days)
            scored.append((candidate.doc_id, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _overlap_score(query_tokens: list[str], text_tokens: list[str]) -> float:
    if not text_tokens:
        return 0.0
    text_set = set(text_tokens)
    overlap = sum(1 for token in query_tokens if token in text_set)
    return overlap / math.sqrt(len(query_tokens) * len(text_tokens))
