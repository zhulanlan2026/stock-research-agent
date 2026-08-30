from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

TOKEN_RE = re.compile(r"[a-zA-Z0-9_\u4e00-\u9fff]+")


class BM25Index:
    """轻量确定性 BM25 索引，后续可替换为 Milvus Sparse。"""

    def __init__(self, *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._docs: dict[str, dict[str, int]] = {}
        self._doc_lengths: dict[str, int] = {}
        self._df: dict[str, int] = defaultdict(int)
        self._avgdl = 0.0

    def add_document(self, doc_id: str, text: str) -> None:
        tokens = _tokenize(text)
        if not tokens:
            return
        counts = Counter(tokens)
        self._docs[doc_id] = dict(counts)
        self._doc_lengths[doc_id] = len(tokens)
        for token in counts:
            self._df[token] += 1
        total_length = sum(self._doc_lengths.values())
        self._avgdl = total_length / len(self._doc_lengths)

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        query_tokens = _tokenize(query)
        if not query_tokens or not self._docs:
            return []

        scores: dict[str, float] = {}
        n_docs = len(self._docs)
        for token in set(query_tokens):
            df = self._df.get(token, 0)
            if df == 0:
                continue
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
            for doc_id, term_counts in self._docs.items():
                tf = term_counts.get(token, 0)
                if tf == 0:
                    continue
                doc_len = self._doc_lengths[doc_id]
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * doc_len / self._avgdl
                )
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * (
                    tf * (self.k1 + 1) / denominator
                )

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return ranked[:top_k]


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]
