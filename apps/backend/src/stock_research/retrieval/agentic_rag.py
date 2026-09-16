from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

RetrievalCallable = Callable[[str], list[str]]


@dataclass(frozen=True)
class AgenticRagStep:
    query: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class AgenticRagResult:
    evidence_ids: tuple[str, ...]
    steps: tuple[AgenticRagStep, ...]


class AgenticRagService:
    """确定性 Agentic RAG：多轮查询改写、检索、去重和证据链记录。"""

    def retrieve(
        self,
        *,
        query: str,
        symbol: str,
        as_of: datetime,
        retriever: RetrievalCallable,
        max_rounds: int = 3,
    ) -> AgenticRagResult:
        queries = _query_variants(query, symbol, as_of)[:max_rounds]
        seen: dict[str, None] = {}
        steps: list[AgenticRagStep] = []

        for rewritten in queries:
            ids = retriever(rewritten)
            unique = tuple(dict.fromkeys(ids))
            steps.append(AgenticRagStep(query=rewritten, evidence_ids=unique))
            for evidence_id in unique:
                seen.setdefault(evidence_id, None)

        return AgenticRagResult(
            evidence_ids=tuple(seen.keys()),
            steps=tuple(steps),
        )


def _query_variants(
    query: str,
    symbol: str,
    as_of: datetime,
) -> list[str]:
    return [
        query,
        f"{symbol} {query}",
        f"{symbol} {query} {as_of.year}",
        f"{symbol} 财务 风险 供应链 {query}",
    ]
