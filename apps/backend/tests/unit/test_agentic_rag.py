from datetime import datetime, timezone

from stock_research.retrieval.agentic_rag import AgenticRagService


def test_agentic_rag_rewrites_dedupes_and_builds_trace() -> None:
    def retriever(query: str) -> list[str]:
        if query.startswith("600519.SH"):
            if "2026" in query:
                return ["e3"]
            return ["e1", "e2"]
        if "财务" in query:
            return ["e3"]
        return ["e1"]

    result = AgenticRagService().retrieve(
        query="供应链风险",
        symbol="600519.SH",
        as_of=datetime(2026, 9, 12, tzinfo=timezone.utc),
        retriever=retriever,
        max_rounds=3,
    )

    assert result.evidence_ids == ("e1", "e2", "e3")
    assert len(result.steps) == 3
    assert result.steps[0].query == "供应链风险"
    assert result.steps[0].evidence_ids == ("e1",)
    assert result.steps[1].evidence_ids == ("e1", "e2")
