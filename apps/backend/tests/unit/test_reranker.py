from stock_research.retrieval.reranker import LexicalReranker, RerankCandidate


def test_lexical_reranker_ranks_relevant_text_higher() -> None:
    candidates = [
        RerankCandidate("a", "白酒 营收 稳定"),
        RerankCandidate("b", "新能源汽车 电池"),
    ]

    result = LexicalReranker().rerank(candidates, "白酒 营收")

    assert result[0][0] == "a"


def test_lexical_reranker_uses_authority_and_freshness() -> None:
    candidates = [
        RerankCandidate("old", "营收", authority_score=0.0, age_days=1000),
        RerankCandidate("new", "营收", authority_score=0.0, age_days=0),
    ]

    result = LexicalReranker().rerank(candidates, "营收")

    assert result[0][0] == "new"


def test_lexical_reranker_handles_empty_query() -> None:
    assert LexicalReranker().rerank([], "") == []
