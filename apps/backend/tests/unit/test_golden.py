from datetime import datetime, timezone

import pytest

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
    assert result.n_dcg == 0.0
    assert result.acl_leakage == 0
    assert result.future_leakage == 0


def test_retrieval_evaluator_computes_ndcg() -> None:
    result = RetrievalEvaluator().evaluate(
        queries=[GoldenQuery("白酒 营收", frozenset({"a", "b"}))],
        ranked_lists={"白酒 营收": ["a", "c", "b"]},
        allowed_doc_ids=frozenset({"a", "b", "c"}),
        k=3,
    )

    # DCG = 1/log2(2) + 0 + 1/log2(4) = 1 + 0.5 = 1.5
    # IDCG = 1/log2(2) + 1/log2(3) = 1 + 0.63093 = 1.63093
    assert result.n_dcg == pytest.approx(1.5 / 1.63093, abs=1e-4)


def test_retrieval_evaluator_detects_future_leakage() -> None:
    as_of = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = RetrievalEvaluator().evaluate(
        queries=[GoldenQuery("白酒 营收", frozenset({"a"}))],
        ranked_lists={"白酒 营收": ["a", "future"]},
        allowed_doc_ids=frozenset({"a", "future"}),
        document_available_at={
            "a": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "future": datetime(2026, 6, 1, tzinfo=timezone.utc),
        },
        as_of=as_of,
    )

    assert result.future_leakage == 1
