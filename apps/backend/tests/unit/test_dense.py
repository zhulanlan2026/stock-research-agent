import pytest

from stock_research.retrieval.dense import DenseIndex


def test_dense_index_ranks_by_cosine_similarity() -> None:
    index = DenseIndex()
    index.add("a", [1.0, 0.0])
    index.add("b", [0.0, 1.0])

    results = index.search([1.0, 0.0], top_k=2)

    assert results[0][0] == "a"
    assert results[1][0] == "b"


def test_dense_index_handles_zero_vector() -> None:
    index = DenseIndex()
    index.add("zero", [0.0, 0.0])

    assert index.search([1.0, 0.0]) == []


def test_dense_index_rejects_empty_vector() -> None:
    index = DenseIndex()

    with pytest.raises(ValueError):
        index.add("empty", [])
