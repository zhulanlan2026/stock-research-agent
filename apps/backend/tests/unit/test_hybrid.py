from stock_research.retrieval.bm25 import BM25Index
from stock_research.retrieval.dense import DenseIndex
from stock_research.retrieval.hybrid import HybridRetrievalPipeline


def test_hybrid_pipeline_fuses_bm25_and_dense() -> None:
    bm25 = BM25Index()
    bm25.add_document("a", "白酒 营收")
    bm25.add_document("b", "芯片 营收")

    dense = DenseIndex()
    dense.add("b", [1.0, 0.0])
    dense.add("a", [0.0, 1.0])

    pipeline = HybridRetrievalPipeline(bm25=bm25, dense=dense)
    results = pipeline.retrieve("白酒 营收", [0.0, 1.0], top_k=2)

    assert len(results) == 2
    assert "a" in results
    assert "b" in results
