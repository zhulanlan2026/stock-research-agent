from stock_research.retrieval.golden import GoldenQuery, RetrievalEvaluator


def test_retrieval_evaluator_computes_recall_mrr_and_leakage() -> None:
    result = RetrievalEvaluator().evaluate(
        queries=[
            GoldenQuery("白酒 营收", frozenset({"a", "b"})),
        ],
        ranked_lists={
            "白酒 营收": ["x", "a", "c"],
        },
        allowed_doc_ids=frozenset({"a", "b", "c"}),
        k=3,
    )

    assert result.recall_at_k == 0.5
    assert result.mrr == 0.5
    assert result.acl_leakage == 1


def test_retrieval_evaluator_handles_empty_dataset() -> None:
    result = RetrievalEvaluator().evaluate(
        queries=[],
        ranked_lists={},
        allowed_doc_ids=frozenset(),
    )

    assert result.recall_at_k == 0.0
    assert result.mrr == 0.0
    assert result.acl_leakage == 0
