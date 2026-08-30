from stock_research.retrieval.bm25 import BM25Index


def test_bm25_ranks_relevant_document_first() -> None:
    index = BM25Index()
    index.add_document("doc-1", "白酒 营收 增长 稳定")
    index.add_document("doc-2", "新能源汽车 电池 供应链")

    results = index.search("白酒 营收")

    assert results
    assert results[0][0] == "doc-1"


def test_bm25_handles_empty_index_and_query() -> None:
    index = BM25Index()

    assert index.search("anything") == []
    index.add_document("doc-1", "hello world")
    assert index.search("") == []


def test_bm25_is_deterministic() -> None:
    first = BM25Index()
    second = BM25Index()
    for index in (first, second):
        index.add_document("a", "hello world")
        index.add_document("b", "world finance")

    assert first.search("world finance") == second.search("world finance")
